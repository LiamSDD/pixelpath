import struct
import zlib

import pytest

from pixelpath.png import PNGError, decode_png, encode_png

SIGNATURE = b"\x89PNG\r\n\x1a\n"


def iterate_chunks(data):
    position = len(SIGNATURE)
    while position < len(data):
        (length,) = struct.unpack(">I", data[position : position + 4])
        kind = data[position + 4 : position + 8]
        body = data[position + 8 : position + 8 + length]
        (crc,) = struct.unpack(">I", data[position + 8 + length : position + 12 + length])
        yield kind, body, crc
        position += 12 + length


def sample_pixels():
    return bytes([255, 0, 0, 255, 0, 255, 0, 128, 0, 0, 255, 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120])


def test_signature_and_chunk_order():
    data = encode_png(3, 2, sample_pixels())
    assert data.startswith(SIGNATURE)
    kinds = [kind for kind, _, _ in iterate_chunks(data)]
    assert kinds[0] == b"IHDR"
    assert kinds[-1] == b"IEND"
    assert b"IDAT" in kinds


def test_every_chunk_crc_is_correct():
    data = encode_png(3, 2, sample_pixels())
    for kind, body, crc in iterate_chunks(data):
        assert zlib.crc32(kind + body) & 0xFFFFFFFF == crc


def test_ihdr_describes_rgba_8bit_image():
    data = encode_png(3, 2, sample_pixels())
    kind, body, _ = next(iterate_chunks(data))
    assert kind == b"IHDR"
    assert struct.unpack(">IIBBBBB", body) == (3, 2, 8, 6, 0, 0, 0)


def test_round_trip():
    width, height, pixels = decode_png(encode_png(3, 2, sample_pixels()))
    assert (width, height) == (3, 2)
    assert pixels == sample_pixels()


def test_decoder_detects_corruption():
    data = bytearray(encode_png(3, 2, sample_pixels()))
    data[20] ^= 0xFF
    with pytest.raises(PNGError):
        decode_png(bytes(data))


def test_decoder_rejects_non_png():
    with pytest.raises(PNGError):
        decode_png(b"not a png at all")


def test_encoder_rejects_wrong_buffer_size():
    with pytest.raises(ValueError):
        encode_png(2, 2, b"\x00" * 15)


def test_encoder_rejects_empty_dimensions():
    with pytest.raises(ValueError):
        encode_png(0, 1, b"")


def test_decoder_handles_all_filter_types():
    width, height = 2, 5
    rows = [bytes(range(row * 8, row * 8 + 8)) for row in range(height)]
    raw = b"".join(bytes([0]) + row for row in rows[:1])
    previous = rows[0]
    for filter_type, row in zip([1, 2, 3, 4], rows[1:]):
        filtered = bytearray()
        for index, value in enumerate(row):
            left = row[index - 4] if index >= 4 else 0
            up = previous[index]
            up_left = previous[index - 4] if index >= 4 else 0
            if filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            else:
                estimate = left + up - up_left
                distances = (abs(estimate - left), abs(estimate - up), abs(estimate - up_left))
                predictor = (left, up, up_left)[distances.index(min(distances))]
            filtered.append((value - predictor) & 0xFF)
        raw += bytes([filter_type]) + bytes(filtered)
        previous = row

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    data = SIGNATURE + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    assert decode_png(data) == (width, height, b"".join(rows))
