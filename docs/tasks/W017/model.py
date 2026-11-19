"""Investigation subset. All spatial math uses integer DBU or exact nominal nm."""
from dataclasses import dataclass
from fractions import Fraction

from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.geometry import Rect
from layauto_v2.importers.config import load_document
from layauto_v2.normalization.geometry import GeometryResult


class Issue(ValueError):
    def __init__(self, status, field, value):
        self.detail = dict(status=status, field=field, value=value)
        super().__init__(str(self.detail))


def require(ok, field, value):
    if not ok:
        raise Issue("invalid_declaration", field, value)


def fields(node, allowed, path):
    require(isinstance(node, FrozenMap) and set(node) == set(allowed), path, "fields")


@dataclass(frozen=True)
class Edges:
    first: int
    pitch: int
    cells: int

    def span(self, low, high, dim):
        end = self.first + self.pitch * self.cells
        if low < self.first or high > end:
            raise Issue("outside_range", dim, [low, high])
        return range((low - self.first) // self.pitch, -((self.first - high) // self.pitch))


def cover(x_axis, y_axis, rect, remaining):
    xs = x_axis.span(rect.x0, rect.x1, "x")
    ys = y_axis.span(rect.y0, rect.y1, "y")
    count = (xs.stop - xs.start) * (ys.stop - ys.start)
    if count > remaining:
        raise Issue("resource_limit", "fragments", count)
    for i in xs:
        left = x_axis.first + i * x_axis.pitch
        for j in ys:
            lower = y_axis.first + j * y_axis.pitch
            cell = Rect(left, lower, left + x_axis.pitch, lower + y_axis.pitch)
            yield i, j, rect.intersection(cell)


@dataclass(frozen=True)
class Tracks:
    phase_nm: Fraction
    pitch_nm: int
    first: int
    last: int

    def centre(self, index):
        if type(index) is not int:
            raise Issue("invalid_query", "index", repr(index))
        if not self.first <= index <= self.last:
            raise Issue("outside_range", "index", index)
        return self.phase_nm + index * self.pitch_nm

    def locate(self, y_nm):
        if type(y_nm) not in (int, Fraction):
            raise Issue("invalid_query", "y_nm", repr(y_nm))
        position = (Fraction(y_nm) - self.phase_nm) / self.pitch_nm
        result = {"y_nm": str(y_nm)}
        if not self.first <= position <= self.last:
            return dict(result, status="outside_range")
        if position.denominator == 1:
            return dict(result, status="on_track", index=int(position))
        low = position.numerator // position.denominator
        return dict(result, status="off_track", adjacent=[
            {"index": k, "delta_nm": str(y_nm - self.centre(k))} for k in (low, low + 1)])


BINDINGS = {"tech.json", "tech/drawn.json", "tech/formats.json", "tech/coordinate.json",
            "tech/physical.json", "source.gds"}


def bind(selection, candidate, geometry):
    """Take geometry and captured owners from the same successful W008 receipt."""
    if type(geometry) is not GeometryResult or geometry.status != "success":
        raise ValueError("expected successful W008 geometry")
    layout = geometry.layout
    captured = geometry.input.parse.sources
    sel = load_document(selection)
    fields(sel, ("schema", "uri", "sha256"), "/")
    require(sel["schema"] == "w017-selection/1", "/schema", sel["schema"])
    require((sel["uri"], sel["sha256"]) == (candidate.uri, candidate.sha256),
            "/sha256", candidate.sha256)
    doc = load_document(candidate)
    fields(doc, ("schema", "classification", "bindings", "axes", "layers"), "/")
    require(doc["schema"] == "w017-coordinate-proposal/1", "/schema", doc["schema"])
    require(doc["classification"] == "synthetic", "/classification", doc["classification"])
    fields(doc["bindings"], BINDINGS, "/bindings")
    sources = {source.uri: source for source in captured}
    for uri, sha in doc["bindings"].items():
        require(uri in sources and sources[uri].sha256 == sha, "/bindings/" + uri.replace("/", "~1"), sha)
    origin = load_document(sources["tech/coordinate.json"])["coordinate_projection"]["frame_origin_nm"]
    profile = load_document(sources["tech/physical.json"])["fin_count_profile"]
    axes = {}
    require(isinstance(doc["axes"], FrozenMap), "/axes", "expected object")
    for name, row in doc["axes"].items():
        path = "/axes/" + name
        require(isinstance(row, FrozenMap), path, "expected object")
        kind = row.get("kind")
        dim = row.get("dimension")
        require(dim in ("x", "y"), path + "/dimension", dim)
        if kind == "regular_edges_dbu":
            fields(row, ("kind", "dimension", "offset", "pitch", "cells"), path)
            for key in ("pitch", "cells", "offset"):
                value = row[key]
                require(type(value) is int and (key == "offset" or value > 0), path + "/" + key, value)
            start = layout.units.nm_to_canonical(origin[("x", "y").index(dim)]) + row["offset"]
            axis = Edges(start, row["pitch"], row["cells"])
        elif kind == "fin_centres_from_profile":
            fields(row, ("kind", "dimension", "indices"), path)
            require(dim == "y", path + "/dimension", dim)
            indices = row["indices"]
            require(isinstance(indices, tuple) and len(indices) == 2 and
                    all(type(k) is int for k in indices) and indices[0] <= indices[1],
                    path + "/indices", indices)
            require(origin == (0, 0), "/coordinate_projection/frame_origin_nm", origin)
            phase = profile["fin_lower_edge_offset_nm"] + Fraction(profile["fin_width_nm"], 2)
            axis = Tracks(phase, profile["fin_pitch_nm"], *indices)
        else:
            raise Issue("invalid_declaration", path + "/kind", kind)
        axes[name] = (dim, axis)

    resolved = {}
    require(isinstance(doc["layers"], FrozenMap), "/layers", "expected object")
    policies = {p.name: p for p in layout.policies}
    for layer, refs in doc["layers"].items():
        path = "/layers/" + layer
        require(layer in policies and policies[layer].projected, path, layer)
        is_fin = layer == "FIN"
        require(is_fin or policies[layer].declaration["tier"] == "B", path, layer)
        required = ("track",) if is_fin else ("x", "y")
        require(isinstance(refs, FrozenMap) and set(refs) <= set(required), path, "fields")
        selected = {}
        for key, name in refs.items():
            field = path + "/" + key
            require(type(name) is str and name in axes, field, name)
            dim, axis = axes[name]
            require(isinstance(axis, Tracks if is_fin else Edges) and dim == ("y" if is_fin else key),
                    field, name)
            selected[key] = axis
        resolved[layer] = selected
    return resolved


def axes_for(model, layer, keys):
    result = model.get(layer, {})
    for key in keys:
        if key not in result:
            raise Issue("missing_axis", "/layers/" + layer + "/" + key, None)
    return tuple(result[key] for key in keys)
