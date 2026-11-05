"""Pure semantic, drawn-base and effective-region drafts (partial Stage 2)."""
from .component import normalize
from .input import from_inputs_ready, from_parse_result
from .contracts import NormalizationInput, NormalizationResult
from .geometry_input import (
    GeometryInput, GeometryInputError, geometry_from_parse_result,
    geometry_from_inputs_ready, geometry_from_normalization_input,
)
from .geometry import GeometryResult, build_geometry
from .effective import EffectiveGeometryResult, build_effective_geometry
from .local_connectivity import LocalConnectivityResult, build_local_connectivity

__all__ = ['normalize', 'from_inputs_ready', 'from_parse_result', 'NormalizationInput', 'NormalizationResult',
           'GeometryInput', 'GeometryInputError', 'GeometryResult', 'build_geometry',
           'geometry_from_parse_result', 'geometry_from_inputs_ready', 'geometry_from_normalization_input',
           'EffectiveGeometryResult', 'build_effective_geometry',
           'LocalConnectivityResult', 'build_local_connectivity']
