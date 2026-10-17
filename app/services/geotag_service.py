"""Geotagged photos: read (and, for tests and the demo script, write) the GPS position inside a JPEG.

Phones store the place where a photo was taken in the photo's EXIF data. We read that position
with plain Python, so no extra package is needed. Only JPEG files are supported, because that
is what phone cameras produce. A PNG or WebP photo has no GPS position for us to read.
"""
import math
import struct

# EXIF value types we need: (size in bytes of one value)
_TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8}
_GPS_POINTER_TAG = 0x8825
_EXIF_HEADER = b"Exif\x00\x00"


def distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Straight-line distance over the earth's surface (haversine formula)."""
    radius = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


# ---------------------------------------------------------------- reading


def _find_exif_segment(jpeg: bytes) -> bytes | None:
    """Returns the TIFF block inside the JPEG's Exif segment, or None."""
    if not jpeg.startswith(b"\xff\xd8"):
        return None
    position = 2
    while position + 4 <= len(jpeg):
        if jpeg[position] != 0xFF:
            return None
        marker = jpeg[position + 1]
        if marker == 0xFF:  # padding byte
            position += 1
            continue
        if marker == 0xDA or marker == 0xD9:  # start of image data / end of image: no more headers
            return None
        (length,) = struct.unpack(">H", jpeg[position + 2 : position + 4])
        segment = jpeg[position + 4 : position + 2 + length]
        if marker == 0xE1 and segment.startswith(_EXIF_HEADER):
            return segment[len(_EXIF_HEADER) :]
        position += 2 + length
    return None


class _Tiff:
    def __init__(self, data: bytes):
        if data[:2] == b"II":
            self.order = "<"
        elif data[:2] == b"MM":
            self.order = ">"
        else:
            raise ValueError("not a TIFF block")
        self.data = data
        if self.unpack("H", 2) != 42:
            raise ValueError("bad TIFF magic")

    def unpack(self, fmt: str, offset: int):
        size = struct.calcsize(fmt)
        if offset < 0 or offset + size > len(self.data):
            raise ValueError("offset outside the data")
        return struct.unpack(self.order + fmt, self.data[offset : offset + size])[0]

    def read_ifd(self, offset: int) -> dict:
        """Returns {tag: (type, count, position_of_the_value_bytes)}."""
        entries = {}
        for index in range(self.unpack("H", offset)):
            base = offset + 2 + index * 12
            tag = self.unpack("H", base)
            kind = self.unpack("H", base + 2)
            count = self.unpack("I", base + 4)
            size = _TYPE_SIZES.get(kind, 0) * count
            position = base + 8 if size <= 4 else self.unpack("I", base + 8)
            entries[tag] = (kind, count, position)
        return entries

    def text(self, entry) -> str:
        _, count, position = entry
        return self.data[position : position + count].split(b"\x00")[0].decode("ascii", "ignore")

    def degrees(self, entry) -> float:
        kind, count, position = entry
        if kind != 5 or count != 3:
            raise ValueError("GPS coordinate must be 3 rationals")
        parts = []
        for index in range(3):
            numerator = self.unpack("I", position + index * 8)
            denominator = self.unpack("I", position + index * 8 + 4)
            parts.append(numerator / denominator if denominator else 0.0)
        return parts[0] + parts[1] / 60 + parts[2] / 3600


def read_gps(jpeg: bytes) -> tuple[float, float] | None:
    """Returns (latitude, longitude) stored in the photo, or None if there is none.

    Never raises: a broken or unusual file simply means "no usable location".
    """
    try:
        block = _find_exif_segment(jpeg)
        if block is None:
            return None
        tiff = _Tiff(block)
        ifd0 = tiff.read_ifd(tiff.unpack("I", 4))
        if _GPS_POINTER_TAG not in ifd0:
            return None
        gps_offset = tiff.unpack("I", ifd0[_GPS_POINTER_TAG][2])
        gps = tiff.read_ifd(gps_offset)
        if not all(tag in gps for tag in (1, 2, 3, 4)):
            return None
        latitude = tiff.degrees(gps[2]) * (-1 if tiff.text(gps[1]).upper() == "S" else 1)
        longitude = tiff.degrees(gps[4]) * (-1 if tiff.text(gps[3]).upper() == "W" else 1)
    except (ValueError, struct.error, IndexError):
        return None

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    if latitude == 0 and longitude == 0:
        return None  # many cameras write 0,0 when they had no GPS fix
    return latitude, longitude


# ---------------------------------------------------------------- writing (tests and demo script)


def _dms_rational(value: float) -> bytes:
    value = abs(value)
    degrees = int(value)
    minutes = int((value - degrees) * 60)
    seconds = round(((value - degrees) * 60 - minutes) * 60 * 10_000)
    pairs = ((degrees, 1), (minutes, 1), (seconds, 10_000))
    return b"".join(struct.pack(">II", number, divisor) for number, divisor in pairs)


def _build_exif_segment(latitude: float, longitude: float) -> bytes:
    gps_offset = 26  # right after the 18-byte IFD0
    data_start = gps_offset + 2 + 4 * 12 + 4

    def entry(tag, kind, count, value: bytes) -> bytes:
        return struct.pack(">HHI", tag, kind, count) + value

    gps_entries = [
        entry(1, 2, 2, b"S\x00\x00\x00" if latitude < 0 else b"N\x00\x00\x00"),
        entry(2, 5, 3, struct.pack(">I", data_start)),
        entry(3, 2, 2, b"W\x00\x00\x00" if longitude < 0 else b"E\x00\x00\x00"),
        entry(4, 5, 3, struct.pack(">I", data_start + 24)),
    ]
    tiff = (
        b"MM\x00\x2a" + struct.pack(">I", 8)
        + struct.pack(">H", 1) + entry(_GPS_POINTER_TAG, 4, 1, struct.pack(">I", gps_offset)) + struct.pack(">I", 0)
        + struct.pack(">H", 4) + b"".join(gps_entries) + struct.pack(">I", 0)
        + _dms_rational(latitude) + _dms_rational(longitude)
    )
    body = _EXIF_HEADER + tiff
    return b"\xff\xe1" + struct.pack(">H", len(body) + 2) + body


def write_gps(jpeg: bytes, latitude: float, longitude: float) -> bytes:
    """Returns a copy of the JPEG that carries the given position. Replaces any old Exif block."""
    if not jpeg.startswith(b"\xff\xd8"):
        raise ValueError("Only JPEG files can be geotagged")
    kept = []
    position = 2
    while position + 4 <= len(jpeg) and jpeg[position] == 0xFF and jpeg[position + 1] not in (0xDA, 0xD9):
        (length,) = struct.unpack(">H", jpeg[position + 2 : position + 4])
        segment = jpeg[position : position + 2 + length]
        if not (jpeg[position + 1] == 0xE1 and segment[4:10] == _EXIF_HEADER):
            kept.append(segment)
        position += 2 + length
    # JFIF (APP0) must stay first, so the Exif block goes right after it
    first = kept[0] if kept and kept[0][1] == 0xE0 else b""
    rest = kept[1:] if first else kept
    return b"\xff\xd8" + first + _build_exif_segment(latitude, longitude) + b"".join(rest) + jpeg[position:]
