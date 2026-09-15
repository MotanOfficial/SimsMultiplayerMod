import unittest

from simmp import messages as msg
from simmp.constants import PROTOCOL_VERSION
from simmp.validation import ProtocolError, validate_message


class ValidationTests(unittest.TestCase):
    def assert_protocol_error(self, message, code):
        with self.assertRaises(ProtocolError) as catch:
            validate_message(message)
        self.assertEqual(catch.exception.code, code)

    def test_valid_messages_pass(self):
        for message in [
            msg.make_hello("A", "1.0"),
            msg.make_hello("A", "1.0", client_id="stable-client-id"),
            msg.make_welcome(1, "lobby", 1.0),
            msg.make_ping(1.0),
            msg.make_pong(1.0, 2.0),
            msg.make_join_room("lobby"),
            msg.make_room_state("lobby", [{"player_id": 1, "name": "A", "connected": True}]),
            msg.make_player_joined(1, "A", "lobby"),
            msg.make_player_left(1, "lobby", "ok"),
            msg.make_event("test", "hello"),
            msg.make_event("test", "hello", seq=3, player_id=7),
            msg.make_event_ack(3, "lobby"),
            msg.make_presence(7, 12),
            msg.make_presence(7, 12, player_id=7, room_id="lobby"),
            msg.make_error("MALFORMED", "x"),
            msg.make_travel_request(1),
            msg.make_travel_invite(1, 2, "Bob"),
            msg.make_travel_response(True),
            msg.make_travel_response(False, reason="busy"),
            msg.make_travel_begin(1),
            msg.make_travel_ready(1),
            msg.make_travel_complete(1),
            msg.make_travel_abort("reason"),
            msg.make_clock_sync(1, 2, 3.0, 1),
            msg.make_clock_sync(1, 2, 3.0, 1, player_id=9),
        ]:
            result = validate_message(message)
            self.assertIs(result, message)

    def test_missing_version(self):
        self.assert_protocol_error({"type": "HELLO", "request_id": "r", "payload": {}}, "MALFORMED")

    def test_wrong_version(self):
        message = msg.make_hello("A", "1.0")
        message["version"] = PROTOCOL_VERSION + 1
        self.assert_protocol_error(message, "INCOMPATIBLE_VERSION")

    def test_unknown_type(self):
        message = msg.make_hello("A", "1.0")
        message["type"] = "NAUGHTY"
        self.assert_protocol_error(message, "UNKNOWN_TYPE")

    def test_missing_payload_field(self):
        message = msg.make_event("test", None)
        del message["payload"]["data"]
        self.assert_protocol_error(message, "MALFORMED")

    def test_unknown_payload_field(self):
        message = msg.make_welcome(1, "lobby", 1.0)
        message["payload"]["bogus"] = True
        self.assert_protocol_error(message, "MALFORMED")

    def test_room_state_players_must_be_list(self):
        message = msg.make_room_state("lobby", [])
        message["payload"]["players"] = "not-a-list"
        self.assert_protocol_error(message, "MALFORMED")

    def test_room_state_player_entry_must_have_fields(self):
        message = {
            "version": PROTOCOL_VERSION,
            "type": "ROOM_STATE",
            "request_id": "r",
            "payload": {"room_id": "lobby", "players": [{"player_id": 1}]},
        }
        self.assert_protocol_error(message, "MALFORMED")

    def test_hello_bad_protocol_version(self):
        message = msg.make_hello("A", "1.0")
        message["payload"]["protocol_version"] = 99
        self.assert_protocol_error(message, "INCOMPATIBLE_VERSION")

    def test_name_too_long(self):
        message = {
            "version": PROTOCOL_VERSION,
            "type": "HELLO",
            "request_id": "r",
            "payload": {"client_name": "X" * 200, "client_version": "1.0", "protocol_version": PROTOCOL_VERSION},
        }
        self.assert_protocol_error(message, "MALFORMED")

    def test_request_id_must_be_string(self):
        message = msg.make_hello("A", "1.0")
        message["request_id"] = 123
        self.assert_protocol_error(message, "MALFORMED")

    def test_unknown_top_level_field(self):
        message = msg.make_hello("A", "1.0")
        message["sneaky"] = 1
        self.assert_protocol_error(message, "MALFORMED")

    def test_float_fields_must_be_numbers(self):
        message = msg.make_ping(1.0)
        message["payload"]["client_time"] = {"nope": True}
        self.assert_protocol_error(message, "MALFORMED")

    def test_event_missing_seq_rejected(self):
        message = msg.make_event("test", None)
        del message["payload"]["seq"]
        self.assert_protocol_error(message, "MALFORMED")

    def test_presence_optional_stamp_fields_accepted(self):
        message = msg.make_presence(1, 2, timestamp=3.0)
        validate_message(message)
        message["payload"]["player_id"] = 5
        message["payload"]["room_id"] = "lobby"
        validate_message(message)

    def test_unknown_optional_field_on_event_rejected(self):
        message = msg.make_event("test", None, seq=1)
        message["payload"]["bogus"] = True
        self.assert_protocol_error(message, "MALFORMED")

    def test_client_id_too_long_rejected(self):
        message = {
            "version": PROTOCOL_VERSION,
            "type": "HELLO",
            "request_id": "r",
            "payload": {
                "client_name": "A",
                "client_version": "1.0",
                "protocol_version": PROTOCOL_VERSION,
                "client_id": "X" * 200,
            },
        }
        self.assert_protocol_error(message, "MALFORMED")

    def test_client_id_non_string_rejected(self):
        message = msg.make_hello("A", "1.0")
        message["payload"]["client_id"] = 7
        self.assert_protocol_error(message, "MALFORMED")

    def test_travel_response_accept_must_be_bool(self):
        message = msg.make_travel_response(True)
        message["payload"]["accepted"] = "yes"
        self.assert_protocol_error(message, "MALFORMED")

    def test_clock_sync_int_fields_must_be_ints(self):
        message = msg.make_clock_sync(1, 2, 3.0, 1)
        message["payload"]["absolute_ticks"] = "soon"
        self.assert_protocol_error(message, "MALFORMED")

    def test_clock_sync_real_time_must_be_number(self):
        message = msg.make_clock_sync(1, 2, 3.0, 1)
        message["payload"]["real_time"] = "now"
        self.assert_protocol_error(message, "MALFORMED")

    def test_travel_zone_id_must_be_int(self):
        message = msg.make_travel_request(1)
        message["payload"]["zone_id"] = "lobby"
        self.assert_protocol_error(message, "MALFORMED")

    def test_travel_abort_reason_string_too_long(self):
        message = {
            "version": PROTOCOL_VERSION,
            "type": "TRAVEL_ABORT",
            "request_id": "r",
            "payload": {"reason": "x" * 600},
        }
        self.assert_protocol_error(message, "MALFORMED")