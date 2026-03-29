"""
Minimal GDS-II binary writer.

Uses only Python stdlib (struct). Supports rectangles (BOUNDARY)
and cell references (SREF). Sufficient for generating dummy layouts.

GDS-II format reference:
  Each record = 2-byte length + 1-byte record_type + 1-byte data_type + data
  Coordinates are 4-byte signed integers in database units.
  
Database unit convention: 1 database unit = 1 nm
"""

import struct
from datetime import datetime
from typing import List, Tuple


# ---- GDS-II record type codes ----
_HEADER   = 0x00
_BGNLIB   = 0x01
_LIBNAME  = 0x02
_UNITS    = 0x03
_ENDLIB   = 0x04
_BGNSTR   = 0x05
_STRNAME  = 0x06
_ENDSTR   = 0x07
_BOUNDARY = 0x08
_SREF     = 0x0A
_ENDEL    = 0x11
_LAYER    = 0x0D
_DATATYPE = 0x0E
_XY       = 0x10
_SNAME    = 0x12
_TEXT     = 0x0C
_TEXTTYPE = 0x16
_STRING   = 0x19

# ---- GDS-II data type codes ----
_DT_NONE   = 0x00
_DT_INT2   = 0x02
_DT_INT4   = 0x03
_DT_REAL8  = 0x05
_DT_STRING = 0x06


def _record(rec_type: int, data_type: int, data: bytes = b'') -> bytes:
    """Build a single GDS-II record."""
    length = 4 + len(data)
    # Records must be even-length
    if length % 2 != 0:
        data += b'\x00'
        length += 1
    return struct.pack('>HBB', length, rec_type, data_type) + data


def _int2(value: int) -> bytes:
    return struct.pack('>h', value)


def _int4(value: int) -> bytes:
    return struct.pack('>i', value)


def _real8(value: float) -> bytes:
    """Convert float to GDS-II 8-byte real format (excess-64 exponent)."""
    if value == 0:
        return b'\x00' * 8
    
    negative = value < 0
    value = abs(value)
    
    # Find exponent (base 16)
    exp16 = 0
    mantissa = value
    if mantissa >= 1:
        while mantissa >= 1:
            mantissa /= 16.0
            exp16 += 1
    else:
        while mantissa < 1.0 / 16.0:
            mantissa *= 16.0
            exp16 -= 1
    
    # Mantissa is now in [1/16, 1)
    # Convert to 56-bit integer
    mant_int = int(mantissa * (2**56))
    
    # Excess-64 exponent
    exp_byte = (exp16 + 64) & 0x7F
    if negative:
        exp_byte |= 0x80
    
    result = struct.pack('>B', exp_byte)
    result += struct.pack('>Q', mant_int)[1:]  # 7 bytes of mantissa
    return result


def _timestamp() -> bytes:
    """12 bytes: year, month, day, hour, minute, second as int16."""
    now = datetime(2025, 1, 1)  # Fixed timestamp for reproducibility
    return struct.pack('>6h', now.year, now.month, now.day,
                       now.hour, now.minute, now.second)


def _string(s: str) -> bytes:
    """Encode string for GDS (pad to even length)."""
    b = s.encode('ascii')
    if len(b) % 2 != 0:
        b += b'\x00'
    return b


class GdsWriter:
    """
    Simple GDS-II file writer.
    
    Usage:
        w = GdsWriter('output.gds')
        w.begin_lib('MYLIB')
        w.begin_cell('INV')
        w.rectangle(layer=1, datatype=0, x1=0, y1=0, x2=100, y2=50)
        w.end_cell()
        w.end_lib()
    
    All coordinates are in database units (1 dbu = 1 nm).
    """
    
    def __init__(self, filename: str, dbu_nm: float = 1.0):
        """
        Args:
            filename: Output GDS file path
            dbu_nm: Database unit in nanometers (default: 1nm)
        """
        self.filename = filename
        self.dbu_nm = dbu_nm
        self._data = bytearray()
    
    def begin_lib(self, libname: str = 'DUMMY_LIB'):
        """Write library header."""
        # HEADER - GDS version 600
        self._data += _record(_HEADER, _DT_INT2, _int2(600))
        # BGNLIB - timestamps (modification, access)
        self._data += _record(_BGNLIB, _DT_INT2, _timestamp() + _timestamp())
        # LIBNAME
        self._data += _record(_LIBNAME, _DT_STRING, _string(libname))
        # UNITS - (dbu in user units, dbu in meters)
        # user unit = 1nm = 1e-3 um, dbu in meters = 1e-9
        dbu_m = self.dbu_nm * 1e-9
        user_unit = self.dbu_nm * 1e-3  # in micrometers
        self._data += _record(_UNITS, _DT_REAL8,
                              _real8(user_unit) + _real8(dbu_m))
    
    def end_lib(self):
        """Write library footer and save to file."""
        self._data += _record(_ENDLIB, _DT_NONE)
        with open(self.filename, 'wb') as f:
            f.write(self._data)
    
    def begin_cell(self, cellname: str):
        """Begin a new cell/structure."""
        self._data += _record(_BGNSTR, _DT_INT2, _timestamp() + _timestamp())
        self._data += _record(_STRNAME, _DT_STRING, _string(cellname))
    
    def end_cell(self):
        """End current cell/structure."""
        self._data += _record(_ENDSTR, _DT_NONE)
    
    def rectangle(self, layer: int, datatype: int,
                  x1: int, y1: int, x2: int, y2: int):
        """
        Add a rectangle (as BOUNDARY element).
        
        Args:
            layer, datatype: GDS layer/datatype
            x1, y1: Lower-left corner (dbu)
            x2, y2: Upper-right corner (dbu)
        """
        self._data += _record(_BOUNDARY, _DT_NONE)
        self._data += _record(_LAYER, _DT_INT2, _int2(layer))
        self._data += _record(_DATATYPE, _DT_INT2, _int2(datatype))
        # XY: 5 points (closed rectangle)
        xy_data = b''
        for x, y in [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]:
            xy_data += _int4(x) + _int4(y)
        self._data += _record(_XY, _DT_INT4, xy_data)
        self._data += _record(_ENDEL, _DT_NONE)
    
    def label(self, layer: int, datatype: int,
              x: int, y: int, text: str):
        """Add a text label."""
        self._data += _record(_TEXT, _DT_NONE)
        self._data += _record(_LAYER, _DT_INT2, _int2(layer))
        self._data += _record(_TEXTTYPE, _DT_INT2, _int2(datatype))
        self._data += _record(_XY, _DT_INT4, _int4(x) + _int4(y))
        self._data += _record(_STRING, _DT_STRING, _string(text))
        self._data += _record(_ENDEL, _DT_NONE)


def rect_centered(cx: float, cy: float, width: float, height: float):
    """Helper: compute rectangle corners from center + dimensions."""
    x1 = int(cx - width / 2)
    y1 = int(cy - height / 2)
    x2 = int(cx + width / 2)
    y2 = int(cy + height / 2)
    return x1, y1, x2, y2
