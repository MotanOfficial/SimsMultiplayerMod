import asyncio
import time
import unittest

from simmp import messages as msg
from simmp_client.connectivity import MultiplayerClient
from simmp_client.networking.engine import ClientEngine, EngineState
from server.networking.server import MPServer
from tests.test_server import FakeClient


async def _with_server(callback):
    server = MPServer("127.0.0.1", 0)
    await server.start()
    try:
        await callback(server, server.port)
    finally:
        await server.stop()


async def _wait_until(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        await asyncio.sleep(0.05)
    return False


class ClientEngineTests(unittest.TestCase):
    def run_flow(self, coro):
        asyncio.run(coro)

    def test_engine_lifecycle_with_real_server(self):
        async def flow(server, port):
            received = []
            engine = ClientEngine(
                port=port,
                host="127.0.0.1",
                client_name="Unit",
                on_message=received.append,
            )

            self.assertFalse(engine.connected)
            self.assertTrue(engine.connect(timeout=5.0))
            self.assertTrue(engine.connected)
            self.assertEqual(engine.state, EngineState.CONNECTED)

            ok = await _wait_until(lambda: len(engine._recv) >= 2)
            self.assertTrue(ok, "engine did not receive WELCOME+ROOM_STATE")
            messages = engine.drain()
            types = {m["type"] for m in messages}
            self.assertIn("WELCOME", types)
            self.assertIn("ROOM_STATE", types)

            engine.stop()
            self.assertFalse(engine.connected)
            self.assertTrue(engine.stopped)

        self.run_flow(_with_server(flow))

    def test_engine_seq_ack_and_presence_stream(self):
        async def flow(server, port):
            received = []
            client = MultiplayerClient(client_name="Otto", notify=received.append)
            try:
                ok = client.connect("127.0.0.1", port)
                self.assertTrue(ok)
                ok = await _wait_until(
                    lambda: (client.process_incoming() or True) and client.session.player_id is not None,
                    timeout=5.0,
                )
                self.assertTrue(ok, "client did not receive WELCOME")

                # send_event assigns a seq and keeps the event pending until acked.
                seq = client.engine.send_event("test", "one")
                self.assertIsInstance(seq, int)
                self.assertGreater(seq, 0)
                self.assertEqual(client.engine.pending_count, 1)
                ok = await _wait_until(lambda: client.engine.pending_count == 0, timeout=5.0)
                self.assertTrue(ok, "pending never cleared by EVENT_ACK")
                self.assertEqual(client.engine.pending, {})

                # A peer's presence lands in the local mirror.
                eve = await FakeClient.connect(port, "Eve")
                await eve.send(msg.make_hello("Eve", "t"))
                eve_pid = (await eve.wait_for_type("WELCOME"))["payload"]["player_id"]
                await eve.wait_for_type("ROOM_STATE")
                await eve.send(msg.make_presence(7, 12, timestamp=3.5))
                ok = await _wait_until(
                    lambda: (client.process_incoming() or True) and eve_pid in client.session.presence,
                    timeout=5.0,
                )
                self.assertTrue(ok, "peer presence not mirrored")
                self.assertEqual(client.session.presence[eve_pid]["zone_id"], 7)
                self.assertEqual(client.session.presence[eve_pid]["lot_id"], 12)
            finally:
                client.disconnect()

        self.run_flow(_with_server(flow))

    def test_engine_reconnect_resends_pending_and_keeps_identity(self):
        async def flow(server, port):
            received = []
            client = MultiplayerClient(
                client_name="Otto",
                notify=received.append,
                client_id="PERSISTENT-OTTO",
            )
            try:
                ok = client.connect("127.0.0.1", port)
                self.assertTrue(ok)
                ok = await _wait_until(
                    lambda: (client.process_incoming() or True) and client.session.player_id is not None,
                    timeout=5.0,
                )
                self.assertTrue(ok)
                first_pid = client.session.player_id
                self.assertEqual(client.session.client_id, "PERSISTENT-OTTO")

                eve = await FakeClient.connect(port, "Eve")
                await eve.send(msg.make_hello("Eve", "t"))
                await eve.wait_for_type("WELCOME")
                await eve.wait_for_type("ROOM_STATE")

                # Simulate an event that was never acked: inject it directly
                # into the pending buffer, then force a reconnect.
                client.engine._pending[999] = msg.make_event("test", "injected-999", seq=999)
                self.assertTrue(client.engine.reconnect())

                ok = await _wait_until(
                    lambda: (client.process_incoming() or True)
                    and client.engine.pending_count == 0
                    and client.session.player_id is not None,
                    timeout=8.0,
                )
                self.assertTrue(ok, "pending was not cleared after reconnect")
                # Identity (and therefore server-side dedup) survived.
                self.assertEqual(first_pid, client.session.player_id)

                async def injected_event():
                    while True:
                        message = await asyncio.wait_for(eve.recv(), 8.0)
                        if message["type"] == "EVENT" and message["payload"]["data"] == "injected-999":
                            return message

                event = await injected_event()
                self.assertEqual(event["payload"]["seq"], 999)
                await asyncio.sleep(0.3)
                self.assertEqual(
                    [m for m in eve.messages if m["type"] == "EVENT" and m["payload"]["data"] == "injected-999"],
                    [event],
                )
            finally:
                client.disconnect()

        self.run_flow(_with_server(flow))

    def test_engine_reconnect_from_disconnected_after_server_restart(self):
        async def flow():
            server = MPServer("127.0.0.1", 0)
            await server.start()
            port = server.port
            client = MultiplayerClient(client_name="Otto", client_id="OTTO-2", presence_interval=60.0)
            try:
                self.assertTrue(client.connect("127.0.0.1", port))
                self.assertTrue(await _wait_until(
                    lambda: (client.process_incoming() or True) and client.session.player_id is not None,
                    timeout=5.0,
                ))
                self.assertTrue(client.engine.connected)
            finally:
                await server.stop()

            await asyncio.sleep(0.3)
            self.assertFalse(client.engine.connected)

            # Server is back on the same port; reconnect() must work from the
            # DISCONNECTED state (the engine thread keeps running).
            server2 = MPServer("127.0.0.1", port)
            await server2.start()
            try:
                self.assertTrue(client.engine.reconnect())
                self.assertTrue(await _wait_until(
                    lambda: (client.process_incoming() or True)
                    and client.session.player_id is not None,
                    timeout=8.0,
                ), "engine never re-established from DISCONNECTED")
                self.assertEqual(client.session.client_id, "OTTO-2")
            finally:
                client.disconnect()
                await server2.stop()

        self.run_flow(flow())

    def test_engine_heartbeat_and_event_roundtrip(self):
        async def flow(server, port):
            received = []
            client = MultiplayerClient(client_name="Otto", notify=received.append)
            try:
                ok = client.connect("127.0.0.1", port)
                self.assertTrue(ok)

                ok = await _wait_until(
                    lambda: (client.process_incoming() or True) and client.session.player_id is not None,
                    timeout=5.0,
                )
                self.assertTrue(ok, "client did not receive WELCOME")
                self.assertIsNotNone(client.session.player_id)

                eve = await FakeClient.connect(port, "Eve")
                await eve.send(msg.make_hello("Eve", "t"))
                await eve.wait_for_type("WELCOME")
                await eve.wait_for_type("ROOM_STATE")

                self.assertTrue(client.send_test_event("from-otto"))
                event = await eve.wait_for_type("EVENT")
                self.assertEqual(event["payload"]["data"], "from-otto")

                client.disconnect()
                left = await eve.wait_for_type("PLAYER_LEFT")
                self.assertEqual(left["payload"]["player_id"], client.session.player_id)
            finally:
                client.disconnect()
            self.assertTrue(any("[MP][SYNC]" in line for line in received), "no sync log line emitted")

        self.run_flow(_with_server(flow))


if __name__ == "__main__":
    unittest.main()