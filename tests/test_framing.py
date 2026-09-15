import asyncio
import struct
import unittest

from simmp import framing
from simmp.constants import MAX_FRAME_BYTES


class EncodeDecodeTests(unittest.TestCase):
    def _ping_message(self):
        return {"version": 1, "type": "PING", "request_id": "abc", "payload": {"client_time": 1.5}}

    def test_roundtrip(self):
        message = self._ping_message()
        data = framing.encode(message)
        self.assertEqual(framing.decode(data), message)

    def test_header_length_matches(self):
        message = self._ping_message()
        data = framing.encode(message)
        (length,) = struct.unpack(">I", data[:4])
        self.assertEqual(length, len(data) - 4)

    def test_truncated_frame(self):
        data = framing.encode(self._ping_message())
        with self.assertRaises(framing.FrameError):
            framing.decode(data[:-1])

    def test_length_mismatch(self):
        with self.assertRaises(framing.FrameError):
            framing.decode(struct.pack(">I", 5) + b"abc")

    def test_oversized_encode(self):
        with self.assertRaises(framing.FrameError):
            framing.encode({"big": "x" * (MAX_FRAME_BYTES + 10)})

    def test_encode_at_limit_and_one_over(self):
        # A message whose serialized UTF-8 length is exactly MAX_FRAME_BYTES
        # passes; one byte more is rejected.
        filler = MAX_FRAME_BYTES - len('{"big":""}')
        framing.encode({"big": "x" * filler})
        with self.assertRaises(framing.FrameError):
            framing.encode({"big": "x" * (filler + 1)})

    def test_oversized_header(self):
        body = b"{}"
        with self.assertRaises(framing.FrameError):
            framing.decode(struct.pack(">I", MAX_FRAME_BYTES + 1) + body)

    def test_non_object_json(self):
        body = b"[1, 2, 3]"
        with self.assertRaises(framing.FrameError):
            framing.decode(struct.pack(">I", len(body)) + body)

    def test_invalid_json(self):
        body = b'{"a":'
        with self.assertRaises(framing.FrameError):
            framing.decode(struct.pack(">I", len(body)) + body)


class StreamReadTests(unittest.TestCase):
    def _message(self):
        return {"version": 1, "type": "PING", "request_id": "r", "payload": {"client_time": 1.0}}

    def test_read_frame_byte_by_byte(self):
        async def flow():
            reader = asyncio.StreamReader()
            data = framing.encode(self._message())
            for chunk in data:
                reader.feed_data(bytes([chunk]))
            message = await framing.read_frame(reader)
            self.assertEqual(message, self._message())
            reader.feed_eof()
            self.assertIsNone(await framing.read_frame(reader))

        asyncio.run(flow())

    def test_eof_mid_frame(self):
        async def flow():
            reader = asyncio.StreamReader()
            reader.feed_data(struct.pack(">I", 5))
            reader.feed_eof()
            self.assertIsNone(await framing.read_frame(reader))

        asyncio.run(flow())

    def test_oversized_frame_from_stream(self):
        async def flow():
            reader = asyncio.StreamReader()
            body = b"{}"
            reader.feed_data(struct.pack(">I", MAX_FRAME_BYTES + 1) + body)
            with self.assertRaises(framing.FrameError):
                await framing.read_frame(reader, limit=MAX_FRAME_BYTES)

        asyncio.run(flow())


if __name__ == "__main__":
    unittest.main()