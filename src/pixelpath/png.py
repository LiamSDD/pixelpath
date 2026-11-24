import struct
import zlib
from typing import Tuple

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
COLOR_TYPE_RGBA = 6
BYTES_PER_PIXEL = 4


class PNGError(ValueError):
    pass


def _chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)


def encode_png(width: int, height: int, rgba: bytes, compression_level: int = 6) -> bytes:
    if width <= 0 or height <= 0:
        raise ValueError(f"PNG dimensions must be positive, got {width}x{height}")
    stride = width * BYTES_PER_PIXEL
    if len(rgba) != stride * height:
        raise ValueError(f"expected {stride * height} bytes of RGBA data, got {len(rgba)}")
    view = memoryview(rgba)
    raw = bytearray()
    for row in range(height):
        raw.append(0)
        raw += view[row * stride : (row + 1) * stride]
    header = struct.pack(">IIBBBBB", width, height, 8, COLOR_TYPE_RGBA, 0, 0, 0)
    return (
        PNG_SIGNATURE
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), compression_level))
        + _chunk(b"IEND", b"")
    )


def _paeth(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    distance_left = abs(estimate - left)
    distance_up = abs(estimate - up)
    distance_up_left = abs(estimate - up_left)
    if distance_left <= distance_up and distance_left <= distance_up_left:
        return left
    if distance_up <= distance_up_left:
        return up
    return up_left


def _unfilter(raw: bytes, width: int, height: int) -> bytes:
    stride = width * BYTES_PER_PIXEL
    if len(raw) != (stride + 1) * height:
        raise PNGError("image data has the wrong length")
    output = bytearray(stride * height)
    previous = bytearray(stride)
    for row in range(height):
        offset = row * (stride + 1)
        filter_type = raw[offset]
        line = bytearray(raw[offset + 1 : offset + 1 + stride])
        if filter_type == 1:
            for index in range(BYTES_PER_PIXEL, stride):
                line[index] = (line[index] + line[index - BYTES_PER_PIXEL]) & 0xFF
        elif filter_type == 2:
            for index in range(stride):
                line[index] = (line[index] + previous[index]) & 0xFF
        elif filter_type == 3:
            for index in range(stride):
                left = line[index - BYTES_PER_PIXEL] if index >= BYTES_PER_PIXEL else 0
                line[index] = (line[index] + ((left + previous[index]) >> 1)) & 0xFF
        elif filter_type == 4:
            for index in range(stride):
                left = line[index - BYTES_PER_PIXEL] if index >= BYTES_PER_PIXEL else 0
                up_left = previous[index - BYTES_PER_PIXEL] if index >= BYTES_PER_PIXEL else 0
                line[index] = (line[index] + _paeth(left, previous[index], up_left)) & 0xFF
        elif filter_type != 0:
            raise PNGError(f"unknown filter type {filter_type}")
        output[row * stride : (row + 1) * stride] = line
        previous = line
    return bytes(output)


def decode_png(data: bytes) -> Tuple[int, int, bytes]:
    if not data.startswith(PNG_SIGNATURE):
        raise PNGError("missing PNG signature")
    position = len(PNG_SIGNATURE)
    header = None
    compressed = bytearray()
    ended = False
    while position < len(data):
        if position + 8 > len(data):
            raise PNGError("truncated chunk header")
        (length,) = struct.unpack(">I", data[position : position + 4])
        kind = data[position + 4 : position + 8]
        body_end = position + 8 + length
        if body_end + 4 > len(data):
            raise PNGError(f"truncated {kind!r} chunk")
        body = data[position + 8 : body_end]
        (crc,) = struct.unpack(">I", data[body_end : body_end + 4])
        if zlib.crc32(kind + body) & 0xFFFFFFFF != crc:
            raise PNGError(f"CRC mismatch in {kind!r} chunk")
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            compressed += body
        elif kind == b"IEND":
            ended = True
            break
        position = body_end + 4
    if header is None or not ended:
        raise PNGError("PNG is missing IHDR or IEND")
    width, height, bit_depth, color_type, compression, filter_method, interlace = header
    if (bit_depth, color_type, compression, filter_method, interlace) != (8, COLOR_TYPE_RGBA, 0, 0, 0):
        raise PNGError("only 8-bit non-interlaced RGBA PNGs are supported by this decoder")
    try:
        raw = zlib.decompress(bytes(compressed))
    except zlib.error as error:
        raise PNGError(f"invalid image data: {error}") from error
    return width, height, _unfilter(raw, width, height)
