"""Minimal proto3 wire codec (Motanplayer-owned, no google.protobuf)."""

from __future__ import division

import struct

WIRE_VARINT = 0
WIRE_64BIT = 1
WIRE_LEN = 2
WIRE_32BIT = 5


class WireError(ValueError):
    pass


def _encode_varint(value):
    if value < 0:
        raise WireError("varint must be non-negative")
    out = bytearray()
    while value > 0x7F:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value & 0x7F)
    return bytes(out)


def _decode_varint(buf, index):
    shift = 0
    result = 0
    while True:
        if index >= len(buf):
            raise WireError("truncated varint")
        byte = buf[index]
        index += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return result, index
        shift += 7
        if shift > 70:
            raise WireError("varint too long")


def zigzag_encode(value):
    value = int(value)
    return (value << 1) ^ (value >> 63)


def zigzag_decode(value):
    value = int(value)
    return (value >> 1) ^ (-(value & 1))


def encode_key(field_number, wire_type):
    return _encode_varint((int(field_number) << 3) | int(wire_type))


def encode_varint_field(field_number, value):
    return encode_key(field_number, WIRE_VARINT) + _encode_varint(int(value))


def encode_bool_field(field_number, value):
    return encode_varint_field(field_number, 1 if value else 0)


def encode_sint64_field(field_number, value):
    return encode_varint_field(field_number, zigzag_encode(int(value)) & 0xFFFFFFFFFFFFFFFF)


def encode_fixed64_field(field_number, value):
    return encode_key(field_number, WIRE_64BIT) + struct.pack("<Q", int(value) & 0xFFFFFFFFFFFFFFFF)


def encode_float_field(field_number, value):
    return encode_key(field_number, WIRE_32BIT) + struct.pack("<f", float(value))


def encode_bytes_field(field_number, data):
    if not isinstance(data, (bytes, bytearray)):
        raise WireError("bytes field requires bytes")
    data = bytes(data)
    return encode_key(field_number, WIRE_LEN) + _encode_varint(len(data)) + data


def encode_string_field(field_number, value):
    return encode_bytes_field(field_number, value.encode("utf-8"))


def encode_message(fields):
    out = bytearray()
    for field_number, kind, value in fields:
        if value is None:
            continue
        if kind == "varint":
            out += encode_varint_field(field_number, value)
        elif kind == "bool":
            out += encode_bool_field(field_number, value)
        elif kind == "sint32" or kind == "sint64":
            out += encode_sint64_field(field_number, value)
        elif kind == "fixed64":
            out += encode_fixed64_field(field_number, value)
        elif kind == "float":
            out += encode_float_field(field_number, value)
        elif kind == "bytes" or kind == "message":
            out += encode_bytes_field(field_number, value)
        elif kind == "string":
            out += encode_string_field(field_number, value)
        else:
            raise WireError("unknown field kind %r" % kind)
    return bytes(out)


def decode_fields(buf):
    index = 0
    length = len(buf)
    while index < length:
        key, index = _decode_varint(buf, index)
        field_number = key >> 3
        wire_type = key & 0x07
        if wire_type == WIRE_VARINT:
            value, index = _decode_varint(buf, index)
        elif wire_type == WIRE_64BIT:
            if index + 8 > length:
                raise WireError("truncated 64-bit field")
            value = buf[index:index + 8]
            index += 8
        elif wire_type == WIRE_LEN:
            size, index = _decode_varint(buf, index)
            if index + size > length:
                raise WireError("truncated length-delimited field")
            value = buf[index:index + size]
            index += size
        elif wire_type == WIRE_32BIT:
            if index + 4 > length:
                raise WireError("truncated 32-bit field")
            value = buf[index:index + 4]
            index += 4
        else:
            raise WireError("unsupported wire type %s" % wire_type)
        yield field_number, wire_type, value


def as_varint(value):
    return int(value)


def as_bool(value):
    return bool(value)


def as_sint(value):
    return zigzag_decode(int(value))


def as_fixed64(raw):
    return struct.unpack("<Q", raw)[0]


def as_float(raw):
    return struct.unpack("<f", raw)[0]


def as_bytes(raw):
    return bytes(raw)


def as_string(raw):
    return bytes(raw).decode("utf-8")


decode_message = decode_fields
