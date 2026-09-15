import unittest

from simmp import messages as msg
from simmp.constants import PROTOCOL_VERSION
from simmp.validation import validate_message


class MessageBuilderTests(unittest.TestCase):
    def test_hello_builder(self):
        message = msg.make_hello("Alice", "1.0")
        self.assertEqual(message["version"], PROTOCOL_VERSION)
        self.assertEqual(message["type"], "HELLO")
        self.assertIsInstance(message["request_id"], str)
        self.assertEqual(message["payload"]["client_name"], "Alice")
        self.assertEqual(message["payload"]["protocol_version"], PROTOCOL_VERSION)
        self.assertNotIn("client_id", message["payload"])

    def test_hello_with_client_id(self):
        message = msg.make_hello("Alice", "1.0", client_id="stable-id")
        validate_message(message)
        self.assertEqual(message["payload"]["client_id"], "stable-id")

    def test_welcome_builder(self):
        message = msg.make_welcome(7, "lobby", 1000.5)
        validate_message(message)
        self.assertEqual(message["payload"]["player_id"], 7)
        self.assertEqual(message["payload"]["room_id"], "lobby")

    def test_room_state_builder(self):
        players = [
            {"player_id": 1, "name": "A", "connected": True},
            {"player_id": 2, "name": "B", "connected": True},
        ]
        message = msg.make_room_state("lobby", players)
        validate_message(message)
        self.assertEqual(len(message["payload"]["players"]), 2)

    def test_event_builder_various_data(self):
        for data in (None, "hello", 42, [1, 2, 3], {"a": 1}, True):
            message = msg.make_event("test", data)
            validate_message(message)
            self.assertEqual(message["payload"]["data"], data)

    def test_joined_and_left_builders(self):
        validate_message(msg.make_player_joined(3, "Chris", "lobby"))
        validate_message(msg.make_player_left(3, "lobby", "disconnected"))

    def test_error_builder(self):
        message = msg.make_error("MALFORMED", "something is wrong")
        self.assertEqual(message["payload"]["code"], "MALFORMED")

    def test_ping_pong_builders(self):
        ping = msg.make_ping(1.5)
        self.assertEqual(ping["payload"]["client_time"], 1.5)
        pong = msg.make_pong(1.5, 2.0)
        self.assertEqual(pong["payload"]["client_time"], 1.5)
        self.assertEqual(pong["payload"]["server_time"], 2.0)

    def test_event_ack_builder(self):
        ack = msg.make_event_ack(42, "lobby")
        validate_message(ack)
        self.assertEqual(ack["payload"]["seq"], 42)
        self.assertEqual(ack["payload"]["room_id"], "lobby")

    def test_presence_builder(self):
        presence = msg.make_presence(7, 12, timestamp=1.5)
        validate_message(presence)
        self.assertEqual(presence["payload"]["zone_id"], 7)
        self.assertEqual(presence["payload"]["lot_id"], 12)
        stamped = msg.make_presence(7, 12, timestamp=1.5, player_id=3, room_id="lobby")
        validate_message(stamped)
        self.assertEqual(stamped["payload"]["player_id"], 3)

    def test_event_seq_and_origin_fields(self):
        message = msg.make_event("sim", {"x": 1}, seq=9, player_id=1000)
        validate_message(message)
        self.assertEqual(message["payload"]["seq"], 9)
        self.assertEqual(message["payload"]["player_id"], 1000)

    def test_travel_builders(self):
        request = msg.make_travel_request(4242, request_id_value="t-1")
        validate_message(request)
        self.assertEqual(request["type"], "TRAVEL_REQUEST")
        self.assertEqual(request["request_id"], "t-1")
        self.assertEqual(request["payload"]["zone_id"], 4242)

        invite = msg.make_travel_invite(4242, 1000, "Alice", request_id_value="t-1")
        validate_message(invite)
        self.assertEqual(invite["payload"]["requester_id"], 1000)
        self.assertEqual(invite["payload"]["requester_name"], "Alice")

        for accepted in (True, False):
            response = msg.make_travel_response(accepted, request_id_value="t-1")
            validate_message(response)
            self.assertEqual(response["payload"]["accepted"], accepted)

        declined = msg.make_travel_response(False, reason="busy", request_id_value="t-1")
        validate_message(declined)
        self.assertEqual(declined["payload"]["reason"], "busy")

        validate_message(msg.make_travel_begin(4242, request_id_value="t-1"))
        validate_message(msg.make_travel_ready(4242, request_id_value="t-1"))
        complete = msg.make_travel_complete(4242, request_id_value="t-1")
        validate_message(complete)
        abort = msg.make_travel_abort("no thanks", request_id_value="t-1")
        validate_message(abort)
        self.assertEqual(abort["payload"]["reason"], "no thanks")

    def test_clock_sync_builder(self):
        sync = msg.make_clock_sync(4242, 123456, 98765.5, 1)
        validate_message(sync)
        self.assertEqual(sync["payload"]["absolute_ticks"], 123456)
        self.assertEqual(sync["payload"]["real_time"], 98765.5)
        self.assertEqual(sync["payload"]["clock_speed"], 1)
        self.assertNotIn("player_id", sync["payload"])
        stamped = msg.make_clock_sync(4242, 1, 2, 3, player_id=7)
        validate_message(stamped)
        self.assertEqual(stamped["payload"]["player_id"], 7)

    def test_travel_response_accept_must_be_bool(self):
        with self.assertRaises(Exception):
            msg.make_travel_response("yes", request_id_value="t-1")


    def test_request_ids_are_unique(self):
        self.assertNotEqual(msg.request_id(), msg.request_id())

    def test_default_request_id_present(self):
        message = msg.make_join_room("lobby")
        self.assertIsInstance(message["request_id"], str)


class WorldMessageBuilderTests(unittest.TestCase):
    def test_object_update_builder(self):
        message = msg.make_object_update(
            [{"key": "sofa", "fields": {"x": 1, "y": 2, "z": 3}, "rev": 4}]
        )
        validate_message(message)
        self.assertEqual(message["type"], "OBJECT_UPDATE")
        self.assertEqual(message["payload"]["objects"][0]["fields"]["x"], 1)
        stamped = msg.make_object_update([{"key": "k", "fields": {"x": 0}, "rev": 1}], player_id=3, room_id="lobby")
        validate_message(stamped)
        self.assertEqual(stamped["payload"]["player_id"], 3)
        self.assertEqual(stamped["payload"]["room_id"], "lobby")

    def test_object_claim_release_builders(self):
        claim = msg.make_object_claim("sofa")
        validate_message(claim)
        self.assertEqual(claim["payload"]["key"], "sofa")
        release = msg.make_object_release("sofa")
        validate_message(release)
        self.assertEqual(release["payload"]["key"], "sofa")

    def test_world_state_builder(self):
        objects = [
            {"key": "sofa", "owner": 1000, "fields": {"x": 1.0, "y": 0.0, "z": 0.0}},
            {"key": "table", "owner": None, "fields": {}},
        ]
        message = msg.make_world_state("lobby", objects)
        validate_message(message)
        self.assertEqual(message["type"], "WORLD_STATE")
        self.assertEqual(len(message["payload"]["objects"]), 2)

    def test_world_delta_builder(self):
        message = msg.make_world_delta(
            "lobby", 7, [{"key": "sofa", "fields": {"x": 5.0}}], player_id=1000
        )
        validate_message(message)
        self.assertEqual(message["payload"]["seq"], 7)
        self.assertEqual(message["payload"]["player_id"], 1000)
        self.assertEqual(message["payload"]["updates"][0]["fields"]["x"], 5.0)

    def test_object_ownership_and_claim_ack_builders(self):
        ownership = msg.make_object_ownership("lobby", "sofa", 1000, player_id=1000)
        validate_message(ownership)
        self.assertEqual(ownership["payload"]["owner"], 1000)
        released = msg.make_object_ownership("lobby", "sofa", None, player_id=1000)
        validate_message(released)
        self.assertIsNone(released["payload"]["owner"])
        ack = msg.make_object_claim_ack("sofa", None)
        validate_message(ack)
        self.assertIsNone(ack["payload"]["owner"])


class WorldValidationTests(unittest.TestCase):
    def test_object_update_requires_rev(self):
        with self.assertRaises(Exception):
            msg.make_object_update([{"key": "sofa", "fields": {}}])

    def test_object_update_rejects_non_primitive_fields(self):
        with self.assertRaises(Exception):
            msg.make_object_update([{"key": "sofa", "fields": {"nested": {"a": 1}}, "rev": 1}])

    def test_object_update_rejects_too_many_objects(self):
        objects = [{"key": "k%d" % i, "fields": {"x": 0}, "rev": i} for i in range(17)]
        with self.assertRaises(Exception):
            msg.make_object_update(objects)

    def test_object_update_rejects_long_key_and_field_name(self):
        with self.assertRaises(Exception):
            msg.make_object_update([{"key": "k" * 65, "fields": {}, "rev": 1}])
        with self.assertRaises(Exception):
            msg.make_object_update([{"key": "k", "fields": {"n" * 65: 1}, "rev": 1}])

    def test_object_keys_must_be_non_empty_strings(self):
        with self.assertRaises(Exception):
            msg.make_object_update([{"key": "", "fields": {}, "rev": 1}])
        with self.assertRaises(Exception):
            msg.make_object_claim("")
        with self.assertRaises(Exception):
            msg.make_object_claim(42)

    def test_world_state_requires_valid_owner(self):
        with self.assertRaises(Exception):
            msg.make_world_state("lobby", [{"key": "sofa", "owner": "alice", "fields": {}}])
        with self.assertRaises(Exception):
            msg.make_world_state("lobby", [{"key": "sofa", "fields": {}}])

    def test_world_delta_requires_positive_seq(self):
        with self.assertRaises(Exception):
            msg.make_world_delta("lobby", 0, [{"key": "sofa", "fields": {}}])

    def test_object_ownership_owner_must_be_int_or_null(self):
        with self.assertRaises(Exception):
            msg.make_object_ownership("lobby", "sofa", "bob", player_id=1000)


class InteractionMessageBuilderTests(unittest.TestCase):
    def test_interaction_request_builder(self):
        message = msg.make_interaction_request("sofa", "Read", {"book": "Tome"})
        validate_message(message)
        self.assertEqual(message["type"], "INTERACTION_REQUEST")
        self.assertEqual(message["payload"]["object_key"], "sofa")
        self.assertEqual(message["payload"]["interaction"], "Read")
        self.assertEqual(message["payload"]["args"], {"book": "Tome"})
        bare = msg.make_interaction_request("sofa", "Read")
        self.assertNotIn("args", bare["payload"])

    def test_interaction_end_builder(self):
        message = msg.make_interaction_end("sofa")
        validate_message(message)
        self.assertEqual(message["payload"]["object_key"], "sofa")

    def test_interaction_start_builder(self):
        message = msg.make_interaction_start("lobby", "sofa", "Read", 1000, 123.5, args={"wick": 1})
        validate_message(message)
        self.assertEqual(message["payload"]["player_id"], 1000)
        self.assertEqual(message["payload"]["started_at"], 123.5)
        no_args = msg.make_interaction_start("lobby", "sofa", "Read", 1000, 123.5)
        self.assertNotIn("args", no_args["payload"])
        with_hints = msg.make_interaction_start(
            "lobby",
            "sim:42",
            "Read",
            1000,
            123.5,
            affordance="Read",
            affordance_id=123456789,
            target="sim:7",
        )
        validate_message(with_hints)
        self.assertEqual(with_hints["payload"]["affordance"], "Read")
        self.assertEqual(with_hints["payload"]["affordance_id"], 123456789)
        self.assertEqual(with_hints["payload"]["target"], "sim:7")

    def test_interaction_request_carries_affordance_hints(self):
        message = msg.make_interaction_request(
            "sim:42",
            "Read",
            affordance="Read",
            affordance_id=9001,
            target="sim:7",
        )
        validate_message(message)
        self.assertEqual(message["payload"]["affordance"], "Read")
        self.assertEqual(message["payload"]["affordance_id"], 9001)
        self.assertEqual(message["payload"]["target"], "sim:7")
        bare = msg.make_interaction_request("sim:42", "Read")
        self.assertNotIn("affordance", bare["payload"])
        self.assertNotIn("affordance_id", bare["payload"])
        self.assertNotIn("target", bare["payload"])

    def test_interaction_free_builder(self):
        message = msg.make_interaction_free("lobby", "sofa", 456.0)
        validate_message(message)
        self.assertEqual(message["payload"]["cooldown_until"], 456.0)

    def test_interaction_state_builder(self):
        message = msg.make_interaction_state(
            "lobby",
            [{"object_key": "sofa", "player_id": 1000, "interaction": "Read", "started_at": 1.0}],
        )
        validate_message(message)
        self.assertEqual(len(message["payload"]["interactions"]), 1)
        with_hints = msg.make_interaction_state(
            "lobby",
            [
                {
                    "object_key": "sim:42",
                    "player_id": 1000,
                    "interaction": "Read",
                    "started_at": 1.0,
                    "affordance": "Read",
                    "affordance_id": 99,
                    "target": "sim:7",
                }
            ],
        )
        validate_message(with_hints)
        entry = with_hints["payload"]["interactions"][0]
        self.assertEqual(entry["affordance"], "Read")
        self.assertEqual(entry["affordance_id"], 99)
        self.assertEqual(entry["target"], "sim:7")


class InteractionValidationTests(unittest.TestCase):
    def test_object_key_must_be_non_empty_string(self):
        with self.assertRaises(Exception):
            msg.make_interaction_request("", "Read")
        with self.assertRaises(Exception):
            msg.make_interaction_request(42, "Read")
        with self.assertRaises(Exception):
            msg.make_interaction_end("")

    def test_interaction_type_must_be_non_empty_string(self):
        with self.assertRaises(Exception):
            msg.make_interaction_request("sofa", "")
        with self.assertRaises(Exception):
            msg.make_interaction_request("sofa", 42)

    def test_overlong_key_and_type_rejected(self):
        with self.assertRaises(Exception):
            msg.make_interaction_request("k" * 65, "Read")
        with self.assertRaises(Exception):
            msg.make_interaction_request("sofa", "I" * 129)

    def test_args_must_be_primitive_dict(self):
        with self.assertRaises(Exception):
            msg.make_interaction_request("sofa", "Read", args=[1, 2])
        with self.assertRaises(Exception):
            msg.make_interaction_request("sofa", "Read", args={"nested": {"a": 1}})
        with self.assertRaises(Exception):
            msg.make_interaction_request("sofa", "Read", args={"k" * 65: 1})

    def test_start_requires_int_player_id_and_number_started_at(self):
        with self.assertRaises(Exception):
            msg.make_interaction_start("lobby", "sofa", "Read", "alice", 1.0)
        with self.assertRaises(Exception):
            msg.make_interaction_start("lobby", "sofa", "Read", 1000, "soon")

    def test_state_entries_require_all_fields(self):
        with self.assertRaises(Exception):
            msg.make_interaction_state("lobby", [{"object_key": "sofa", "player_id": 1000, "interaction": "Read"}])
        with self.assertRaises(Exception):
            msg.make_interaction_state("lobby", [{"object_key": "sofa", "player_id": "x", "interaction": "Read", "started_at": 1.0}])

    def test_affordance_hints_are_typed(self):
        with self.assertRaises(Exception):
            msg.make_interaction_request("sim:42", "Read", affordance_id=-1)
        with self.assertRaises(Exception):
            msg.make_interaction_request("sim:42", "Read", affordance_id="9")
        with self.assertRaises(Exception):
            msg.make_interaction_request("sim:42", "Read", affordance=123)
        with self.assertRaises(Exception):
            msg.make_interaction_request("sim:42", "Read", target=7)
        with self.assertRaises(Exception):
            msg.make_interaction_state(
                "lobby",
                [{"object_key": "sim:42", "player_id": 1000, "interaction": "Read", "started_at": 1.0, "affordance_id": "9"}],
            )

    def test_error_ref_is_optional_string(self):
        message = msg.make_error("INTERACTION_BUSY", "sofa is busy", ref="sofa")
        validate_message(message)
        self.assertEqual(message["payload"]["ref"], "sofa")
        bare = msg.make_error("NOPE", "nope")
        self.assertNotIn("ref", bare["payload"])


class SaveMessageBuilderTests(unittest.TestCase):
    def test_save_push_builder(self):
        message = msg.make_save_push("slot_00000001.save", 1, 2, 6, b"abc")
        validate_message(message)
        self.assertEqual(message["type"], "SAVE_PUSH")
        self.assertEqual(message["payload"]["slot"], "slot_00000001.save")
        self.assertEqual(message["payload"]["seq"], 1)
        self.assertEqual(message["payload"]["total"], 2)
        self.assertEqual(message["payload"]["size"], 6)
        self.assertNotIn("origin", message["payload"])
        stamped = msg.make_save_push("slot_00000001.save", 1, 2, 6, b"abc", origin=1000)
        validate_message(stamped)
        self.assertEqual(stamped["payload"]["origin"], 1000)

    def test_save_push_roundtrip_data(self):
        import base64

        message = msg.make_save_push("s.save", 1, 1, 4, b"\x00\x01\x02\xff")
        validate_message(message)
        self.assertEqual(base64.b64decode(message["payload"]["data"]), b"\x00\x01\x02\xff")

    def test_save_ack_builder(self):
        ack = msg.make_save_ack("slot_00000001.save", True, 2)
        validate_message(ack)
        self.assertEqual(ack["type"], "SAVE_ACK")
        self.assertEqual(ack["payload"]["ok"], True)
        self.assertEqual(ack["payload"]["reached"], 2)
        self.assertNotIn("message", ack["payload"])
        with_message = msg.make_save_ack("slot_00000001.save", False, 0, message="disk full")
        validate_message(with_message)
        self.assertEqual(with_message["payload"]["message"], "disk full")


class SaveValidationTests(unittest.TestCase):
    def test_slot_must_be_bare_filename(self):
        for bad in ("../evil.save", "dir/slot.save", "dir\\slot.save", "slot:name.save", "slot\x00.save", ""):
            with self.assertRaises(Exception):
                msg.make_save_push(bad, 1, 1, 0, b"")
        with self.assertRaises(Exception):
            msg.make_save_push("s" * 129 + ".save", 1, 1, 0, b"")

    def test_seq_total_size_ranges(self):
        with self.assertRaises(Exception):
            msg.make_save_push("s.save", 0, 1, 0, b"")
        with self.assertRaises(Exception):
            msg.make_save_push("s.save", 1, 0, 0, b"")
        with self.assertRaises(Exception):
            msg.make_save_push("s.save", 2, 1, 0, b"")  # seq > total
        with self.assertRaises(Exception):
            msg.make_save_push("s.save", 1, 1, -1, b"")

    def test_data_must_be_string_or_missing(self):
        with self.assertRaises(Exception):
            msg.make_save_push("s.save", 1, 1, 0, None)

    def test_save_ack_fields(self):
        with self.assertRaises(Exception):
            msg.make_save_ack("s.save", True, "many")
        with self.assertRaises(Exception):
            msg.make_save_ack("s.save", True, -1)