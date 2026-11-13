"""Unchecked defensive graph clone for a retained-header attack; no file IO."""
from dataclasses import fields, is_dataclass
from layauto_v2.domain.codec import FrozenMap

def alter_retained_header(root, key, replacement):
    memo = {}
    def clone(value):
        if type(value) in (type(None), str, bytes, int, bool, float):
            return value
        identity = id(value)
        if identity in memo:
            return memo[identity]
        if type(value) is FrozenMap:
            result = FrozenMap({name: replacement if name == key else clone(child)
                                for name, child in value.items()})
        elif type(value) is tuple:
            result = tuple(clone(child) for child in value)
        elif is_dataclass(value):
            result = object.__new__(type(value))
            memo[identity] = result
            for field in fields(value):
                object.__setattr__(result, field.name, clone(getattr(value, field.name)))
        else:
            result = value
        memo[identity] = result
        return result
    return clone(root)
