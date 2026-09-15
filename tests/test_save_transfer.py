import asyncio
import os
import tempfile
import unittest

from simmp_client.connectivity import MultiplayerClient
from simmp_client.hooks import game_hooks
from simmp_client.state.save_transfer import SaveInbox, atomic_write
from server.networking.server import MPServer
from tests.test_client_engine import _wait_until


async def _with_server(callback, **kwargs):
    server = MPServer("127.0.0.1", 0, **kwargs)
    await server.start()
    try:
        await callback(server, server.port)
    finally:
        await server.stop()


class SaveInboxTests(unittest.TestCase):
    def test_single_chunk_completes(self):
        inbox = SaveInbox()
        status, data = inbox.feed("s.save", 1, 1, 3, "AQID")
        self.assertEqual(status, "complete")
        self.assertEqual(data, b"\x01\x02\x03")

    def test_multi_chunk_reassembly(self):
        import base64

        inbox = SaveInbox()
        payload = os.urandom(1024)
        chunks = base64.b64encode(payload[:512]).decode("ascii"), base64.b64encode(payload[512:]).decode("ascii")
        self.assertEqual(inbox.feed("s.save", 1, 2, 1024, chunks[0])[0], "more")
        status, data = inbox.feed("s.save", 2, 2, 1024, chunks[1])
        self.assertEqual(status, "complete")
        self.assertEqual(data, payload)
        self.assertEqual(inbox.active(), [])

    def test_out_of_order_chunk_rejected(self):
        import base64

        inbox = SaveInbox()
        chunk = base64.b64encode(b"\x00" * 16).decode("ascii")
        self.assertEqual(inbox.feed("s.save", 1, 2, 32, chunk)[0], "more")
        self.assertEqual(inbox.feed("s.save", 3, 2, 32, chunk)[0], "badseq")

    def test_duplicate_chunk_ignored(self):
        import base64

        inbox = SaveInbox()
        chunk = base64.b64encode(b"\x00" * 16).decode("ascii")
        self.assertEqual(inbox.feed("s.save", 1, 2, 32, chunk)[0], "more")
        self.assertEqual(inbox.feed("s.save", 1, 2, 32, chunk)[0], "duplicate")

    def test_seq_one_restarts_transfer(self):
        import base64

        inbox = SaveInbox()
        chunk = base64.b64encode(b"\x00" * 16).decode("ascii")
        self.assertEqual(inbox.feed("s.save", 1, 2, 32, chunk)[0], "more")
        # An in-flight transfer cannot be hijacked by re-sending seq 1.
        self.assertEqual(inbox.feed("s.save", 1, 1, 16, base64.b64encode(b"x" * 16).decode("ascii"))[0], "duplicate")

    def test_oversized_transfer_never_completes(self):
        import base64

        inbox = SaveInbox()
        chunk = base64.b64encode(b"\x00" * 16).decode("ascii")
        self.assertEqual(inbox.feed("s.save", 1, 2, 16, chunk)[0], "more")
        # second chunk would exceed declared size -> rejected, not completed
        self.assertEqual(inbox.feed("s.save", 2, 2, 16, chunk)[0], "badseq")

    def test_stale_transfer_pruned(self):
        inbox = SaveInbox(window=0.01)
        inbox.feed("s.save", 1, 5, 10, "AAAAAAAA")
        self.assertEqual(inbox.active(), ["s.save"])
        import time

        time.sleep(0.02)
        inbox.feed("other", 1, 2, 2, "AQ==")
        self.assertEqual(inbox.active(), ["other"])


class AtomicWriteTests(unittest.TestCase):
    def test_write_and_replace(self):
        directory = tempfile.mkdtemp()
        path = atomic_write(directory, "slot.save", b"first")
        self.assertTrue(os.path.isfile(path))
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), b"first")
        path = atomic_write(directory, "slot.save", b"second")
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), b"second")

    def test_rejects_non_basename(self):
        directory = tempfile.mkdtemp()
        with self.assertRaises(ValueError):
            atomic_write(directory, "..\\evil.save", b"x")
        with self.assertRaises(ValueError):
            atomic_write(directory, "sub/slot.save", b"x")
        with self.assertRaises(ValueError):
            atomic_write(directory, "", b"x")


class FindSaveDirectoryTests(unittest.TestCase):
    def _trees(self):
        import shutil

        base = tempfile.mkdtemp()
        root = os.path.join(base, "saves")
        profile = os.path.join(root, "Kartoffeln")
        os.makedirs(profile)
        with open(os.path.join(profile, "slot_00000001.save"), "wb") as handle:
            handle.write(b"x")
        return base, root, profile

    def test_plain_root(self):
        base, root, profile = self._trees()
        self.assertEqual(game_hooks.find_save_directory(roots=[root]), profile)

    def test_slot_prefers_matching_folder(self):
        base, root, profile = self._trees()
        other = os.path.join(root, "OtherProfile")
        os.makedirs(other)
        with open(os.path.join(other, "slot_00000009.save"), "wb") as handle:
            handle.write(b"y")
        # The incoming slot lives in Kartoffeln -> must be chosen.
        self.assertEqual(
            game_hooks.find_save_directory(slot="slot_00000001.save", roots=[root]),
            profile,
        )

    def test_missing_roots_resolves_first(self):
        self.assertIsNone(game_hooks.find_save_directory(roots=[]))
        # A single root that does not exist yet is still returned as the
        # fallback so the caller can create it (atomic_write makes dirs).
        self.assertEqual(
            game_hooks.find_save_directory(roots=["C:\\definitely\\missing"]),
            "C:\\definitely\\missing",
        )


class SavePushClientTests(unittest.TestCase):
    def run_flow(self, coro):
        asyncio.run(coro)

    @staticmethod
    async def _connected(client):
        return await _wait_until(
            lambda: (client.process_incoming() or True) and client.session.player_id is not None,
            timeout=5.0,
        )

    def test_push_reaches_peer_and_is_written(self):
        async def flow(server, port):
            alice_log = []
            alice = MultiplayerClient(client_name="Alice", notify=alice_log.append)
            bob = MultiplayerClient(client_name="Bob")
            received = {}

            original = game_hooks.receive_save

            def fake_receive_save(slot, data):
                received[slot] = data
                return "/mock/%s" % slot

            game_hooks.receive_save = fake_receive_save
            try:
                self.assertTrue(alice.connect("127.0.0.1", port))
                self.assertTrue(bob.connect("127.0.0.1", port))
                self.assertTrue(await self._connected(alice))
                self.assertTrue(await self._connected(bob))

                payload = os.urandom(700 * 1024)  # forces 2 chunks
                # Blocking socket writes must not run on the coroutine that owns
                # the asyncio loop (they would starve the server reads).
                sent, total = await self._push_off_loop(alice, "test_slot.save", payload)
                self.assertEqual((sent, total), (2, 2))

                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and received.get("test_slot.save") == payload,
                    timeout=10.0,
                ), "Bob never reassembled the save")

                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and any("SAVE_ACK" in line and "reached=1" in line for line in alice_log),
                    timeout=10.0,
                ), "Alice never saw the reached=1 ack")
            finally:
                game_hooks.receive_save = original

        self.run_flow(_with_server(flow))

    def test_push_solo_reaches_zero(self):
        async def flow(server, port):
            log = []
            alice = MultiplayerClient(client_name="Alice", notify=log.append)
            try:
                self.assertTrue(alice.connect("127.0.0.1", port))
                self.assertTrue(await self._connected(alice))
                sent, total = await self._push_off_loop(alice, "solo.save", b"hi")
                self.assertEqual((sent, total), (1, 1))
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and any("SAVE_ACK" in line and "reached=0" in line for line in log),
                    timeout=10.0,
                ), "Alice never saw the reached=0 ack")
            finally:
                alice.disconnect()

        self.run_flow(_with_server(flow))

    @staticmethod
    async def _push_off_loop(client, slot, payload):
        import concurrent.futures

        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            future = pool.submit(client.push_save_file, slot, payload)
            while not future.done():
                await asyncio.sleep(0.02)
            return future.result()
        finally:
            pool.shutdown()


if __name__ == "__main__":
    unittest.main()