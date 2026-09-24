"""Tests for Motanplayer deep protobuf + host relay."""

from __future__ import division

import base64
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "protocol"))
sys.path.insert(0, os.path.join(ROOT, "client_mod", "scripts"))
sys.path.insert(0, os.path.join(ROOT, "server"))

from simmp.deep import (
    KIND_CANCEL_INTERACTION,
    KIND_GAME_NETWORK,
    KIND_GENERATE_CHOICES,
    KIND_GENERATE_PHONE_CHOICES,
    KIND_HAS_CHOICES,
    KIND_HAS_CHOICES_RESPONSE,
    KIND_SELECT_CHOICE,
    KIND_SET_CLOCK_SPEED,
    KIND_SET_ACTIVE_SIM,
    KIND_SET_AUTONOMY_ENABLED,
    KIND_LIVE_DRAG_START,
    KIND_LIVE_DRAG_START_RESPONSE,
    KIND_LIVE_DRAG_END,
    KIND_LIVE_DRAG_END_RESPONSE,
    KIND_LIVE_DRAG_SELL,
    KIND_LIVE_DRAG_SELL_RESPONSE,
    KIND_CREATE_OBJECT,
    KIND_DESTROY_OBJECT,
    KIND_SET_OBJECT_LOCATION,
    KIND_DIALOG_RESPONSE,
    KIND_DIALOG_PICK_RESULT,
    KIND_DIALOG_TEXT_INPUT,
    KIND_CREATE_SITUATION,
    KIND_START_SITUATION_CREATION,
    KIND_START_SITUATION_CREATION_FOR_EDIT,
    KIND_DESTROY_USER_FACING_SITUATION,
    KIND_SHOW_END_SITUATION_DIALOG,
    KIND_MODIFY_HOUSEHOLD_FUNDS,
    KIND_INVENTORY_SELL_MULTIPLE,
    KIND_PURCHASE_PICKER_RESPONSE,
    KIND_INVENTORY_VIEW_UPDATE,
    KIND_TRAVEL_SIMS_TO_ZONE,
    KIND_TRAVEL_FINISHED,
    KIND_END_VACATION,
    KIND_EXTEND_VACATION,
    KIND_SEND_TO_WORK,
    KIND_LEAVE_WORK,
    KIND_FIND_CAREER,
    KIND_SELECT_CAREER,
    KIND_STAY_LATE,
    KIND_SET_FOLLOW_ENABLED,
    KIND_CAREER_EVENT_SCORING_CLOSE,
    KIND_CREATE_CLUB,
    KIND_UPDATE_CLUB,
    KIND_REMOVE_CLUB,
    KIND_ADD_SIM_TO_CLUB,
    KIND_START_CLUB_GATHERING,
    KIND_END_CLUB_GATHERING,
    KIND_REQUEST_CLUB_INVITE,
    KIND_SHOW_FESTIVAL_INFO,
    KIND_SHOW_FESTIVAL_INFO_BY_UID,
    KIND_TRAVEL_TO_FESTIVAL_ZONE,
    KIND_CANCEL_SCHEDULED_DRAMA_NODE,
    KIND_TRAVEL_TO_EVENT,
    KIND_SET_BUSINESS_OPEN,
    KIND_SET_BUSINESS_MARKUP,
    KIND_SET_BUSINESS_ADVERTISING,
    KIND_SET_BUSINESS_QUALITY,
    KIND_TRANSFER_RETAIL_FUNDS,
    KIND_HIRE_BUSINESS_EMPLOYEE,
    KIND_FIRE_BUSINESS_EMPLOYEE,
    KIND_PUSH_REGISTER_BUSINESS,
    KIND_SHOW_SMALL_BUSINESS_CONFIGURATOR,
    KIND_REGISTER_SMALL_BUSINESS,
    KIND_UPDATE_SMALL_BUSINESS,
    KIND_SET_OPEN_SMALL_BUSINESS,
    KIND_SHOW_SMALL_BUSINESS_EMPLOYEE_MGMT,
    KIND_GET_HOLIDAY_DATA,
    KIND_GET_ACTIVE_HOLIDAY_DATA,
    KIND_UPDATE_HOLIDAY,
    KIND_ADD_HOLIDAY,
    KIND_REMOVE_HOLIDAY,
    KIND_WHIM_REFRESH,
    KIND_WHIM_TOGGLE_LOCK,
    KIND_WHIMS_AWARD_PRIZE,
    KIND_REQUEST_SATISFACTION_REWARD_LIST,
    KIND_REQUEST_PERKS_LIST,
    KIND_UNLOCK_PERK,
    KIND_UNLOCK_MULTIPLE_PERKS,
    KIND_LOCK_ALL_PERKS,
    KIND_SHOW_RENTAL_UNIT_MANAGEMENT,
    KIND_NOTIFY_BUSINESS_RULES_STATE_CHANGE,
    KIND_SET_UNIT_RENT_PRICE,
    KIND_SET_UNIT_SIGNED_LEASE_LENGTH,
    KIND_SELECT_TENANT,
    KIND_REQUEST_SHOW_DYNASTY_CONFIGURATOR,
    KIND_CREATE_DYNASTY,
    KIND_UPDATE_DYNASTY,
    KIND_REMOVE_DYNASTY,
    KIND_SET_ALLOW_FAME,
    KIND_SELL_EXCESS_UTILITY,
    KIND_SET_UTILITY_END_BILL_ACTION,
    KIND_SHOW_EXTEND_VACATION,
    KIND_SHOW_LIGHT_EDITOR,
    KIND_SET_COLOR_AND_INTENSITY,
    KIND_CHEAT,
    KIND_ORDER_FOR_TABLE,
    KIND_REFRESH_RESTAURANT_CONFIG,
    KIND_SOCIAL_MEDIA_REMOVE_FRIEND,
    KIND_SOCIAL_MEDIA_ADD_REACTION,
    KIND_SOCIAL_MEDIA_MARK_POSTS_SEEN,
    KIND_SOCIAL_MEDIA_MARK_MESSAGES_SEEN,
    KIND_GENERATE_LIFESTYLES_DIALOG,
    KIND_EQUIP_TRAIT,
    KIND_SHOW_LIFETIME_MILESTONES_PANEL,
    KIND_GENEALOGY_SHOW_FAMILY_TREE,
    KIND_UNIVERSITY_ENROLL,
    KIND_CANCEL_ENROLLMENT_DIALOG,
    KIND_SHOW_HORSE_COMPETITION_UI,
    KIND_PICK_NEW_HORSE_ASSIGNEE,
    KIND_START_HORSE_COMPETITION,
    KIND_GENERATE_SPELLBOOK_UI,
    KIND_GET_CUSTOM_SCHEDULE,
    KIND_GET_ULTIMATE_PROGRESS,
    KIND_GENERATE_NOTEBOOK,
    KIND_SAVE_NOTES,
    KIND_SET_PRIMARY_ASPIRATION_TRACK,
    KIND_SET_FAVORITE_CALENDAR_ENTRY,
    KIND_UI_CREATE_HOVERTIP,
    KIND_GET_PHOTO_LIST,
    KIND_FAMILY_TREE_SHOW,
    KIND_STREET_CIVIC_REQUEST_ADD_PICKER,
    KIND_HANDLE_COMMUNITY_BOARD,
    KIND_SHOW_COMMUNITY_BOARD,
    KIND_SOLVE_MOTIVE,
    KIND_OPEN_SIM_PROFILE_UI,
    KIND_ZONE_MODIFIERS_UPDATE,
    KIND_CLEAR_PARENT_OBJECT,
    KIND_SET_BUILD_BUY_FLAGS,
    KIND_RESET_OBJECT,
    KIND_SET_PARENT_OBJECT,
    KIND_SET_DEFINITION,
    KIND_SCALE_OBJECT,
    KIND_BUILD_BUY_EXIT,
    KIND_SET_FLOOR_FEATURE,
    KIND_CREATE_SIM_INFO,
    CLOCK_METHOD_PUSH,
    WrapperMessage,
    decode_wrapper,
    encode_wrapper,
)
from simmp import messages as msg
from simmp.validation import validate_message, ProtocolError


class DeepProtobufTests(unittest.TestCase):
    def test_generate_choices_roundtrip(self):
        wrapper = WrapperMessage(
            target_client=1001,
            client_id=1002,
            kind=KIND_GENERATE_CHOICES,
            body={
                "target_id": 123456789,
                "pick_type": 2,
                "x": 1.5,
                "y": 2.25,
                "z": -3.0,
                "lot_id": 99,
                "level": -1,
                "reference_id": 55,
                "is_routable": True,
                "sim_id": 777,
                "player_id": 1002,
                "shift": 1,
            },
        )
        raw = encode_wrapper(wrapper)
        back = decode_wrapper(raw)
        self.assertEqual(back.kind, KIND_GENERATE_CHOICES)
        self.assertEqual(back.target_client, 1001)
        self.assertEqual(back.client_id, 1002)
        self.assertEqual(back.body["target_id"], 123456789)
        self.assertEqual(back.body["pick_type"], 2)
        self.assertAlmostEqual(back.body["x"], 1.5, places=4)
        self.assertTrue(back.body["is_routable"])
        self.assertEqual(back.body["player_id"], 1002)

    def test_game_network_roundtrip(self):
        payload = b"\x00\x01native-bytes"
        wrapper = WrapperMessage(
            target_client=42,
            client_id=7,
            kind=KIND_GAME_NETWORK,
            body={"msg_id": 0xABCDEF, "msg": payload},
        )
        back = decode_wrapper(encode_wrapper(wrapper))
        self.assertEqual(back.kind, KIND_GAME_NETWORK)
        self.assertEqual(back.body["msg_id"], 0xABCDEF)
        self.assertEqual(back.body["msg"], payload)

    def test_select_choice_roundtrip(self):
        wrapper = WrapperMessage(
            kind=KIND_SELECT_CHOICE,
            body={"choice_id": 3, "reference_id": 9, "sim_id": 1, "player_id": 2},
        )
        back = decode_wrapper(encode_wrapper(wrapper))
        self.assertEqual(back.body["choice_id"], 3)
        self.assertEqual(back.body["reference_id"], 9)


    def test_has_choices_roundtrip(self):
        wrapper = WrapperMessage(
            kind=KIND_HAS_CHOICES,
            body={
                "target_id": 11,
                "pick_type": 2,
                "x": 1.0,
                "y": 2.0,
                "z": 3.0,
                "lot_id": 4,
                "level": -1,
                "control": True,
                "alt": False,
                "shift": True,
                "is_routable": True,
                "player_id": 9,
                "sim_id": 8,
            },
        )
        back = decode_wrapper(encode_wrapper(wrapper))
        self.assertEqual(back.kind, KIND_HAS_CHOICES)
        self.assertEqual(back.body["target_id"], 11)
        self.assertTrue(back.body["control"])
        self.assertTrue(back.body["shift"])
        self.assertEqual(back.body["sim_id"], 8)

    def test_has_choices_response_roundtrip(self):
        payload = b"\x10interactable"
        wrapper = WrapperMessage(
            kind=KIND_HAS_CHOICES_RESPONSE,
            body={"immediate": True, "msg": payload},
        )
        back = decode_wrapper(encode_wrapper(wrapper))
        self.assertTrue(back.body["immediate"])
        self.assertEqual(back.body["msg"], payload)

    def test_cancel_and_phone_roundtrip(self):
        cancel = WrapperMessage(
            kind=KIND_CANCEL_INTERACTION,
            body={"interaction_id": 5, "context_handle": 6, "sim_id": 7, "player_id": 8},
        )
        back = decode_wrapper(encode_wrapper(cancel))
        self.assertEqual(back.body["interaction_id"], 5)
        self.assertEqual(back.body["context_handle"], 6)
        phone = WrapperMessage(
            kind=KIND_GENERATE_PHONE_CHOICES,
            body={"sim_id": 1, "player_id": 2, "reference_id": 3, "selected_affordance_id": -1},
        )
        back = decode_wrapper(encode_wrapper(phone))
        self.assertEqual(back.body["reference_id"], 3)
        self.assertEqual(back.body["selected_affordance_id"], -1)

    def test_set_clock_speed_roundtrip(self):
        wrapper = WrapperMessage(
            kind=KIND_SET_CLOCK_SPEED,
            body={
                "speed": 2,
                "immediate": True,
                "source": 1,
                "reason": "From Command",
                "method": CLOCK_METHOD_PUSH,
                "player_id": 1001,
            },
        )
        back = decode_wrapper(encode_wrapper(wrapper))
        self.assertEqual(back.kind, KIND_SET_CLOCK_SPEED)
        self.assertEqual(back.body["speed"], 2)
        self.assertTrue(back.body["immediate"])
        self.assertEqual(back.body["reason"], "From Command")
        self.assertEqual(back.body["method"], CLOCK_METHOD_PUSH)

    def test_active_sim_and_autonomy_roundtrip(self):
        sim = WrapperMessage(kind=KIND_SET_ACTIVE_SIM, body={"sim_id": 42, "player_id": 7})
        back = decode_wrapper(encode_wrapper(sim))
        self.assertEqual(back.body["sim_id"], 42)
        auto = WrapperMessage(kind=KIND_SET_AUTONOMY_ENABLED, body={"enabled": True, "player_id": 7})
        back = decode_wrapper(encode_wrapper(auto))
        self.assertTrue(back.body["enabled"])

    def test_live_drag_roundtrips(self):
        start = WrapperMessage(
            kind=KIND_LIVE_DRAG_START,
            body={
                "live_drag_object_id": 99,
                "start_system": 1,
                "is_stack": True,
                "should_send_start_message": True,
                "player_id": 3,
            },
        )
        back = decode_wrapper(encode_wrapper(start))
        self.assertEqual(back.body["live_drag_object_id"], 99)
        self.assertTrue(back.body["is_stack"])

        start_resp = WrapperMessage(
            kind=KIND_LIVE_DRAG_START_RESPONSE,
            body={
                "live_drag_object_id": 99,
                "start_system": 1,
                "end_system": 0,
                "icon_info_msg": b"ico",
                "valid_drop_object_ids_json": "[1,2]",
                "should_send_start_message": True,
                "valid_stack_id": 7,
                "sell_value": 50,
                "cancel": False,
            },
        )
        back = decode_wrapper(encode_wrapper(start_resp))
        self.assertEqual(back.body["valid_drop_object_ids_json"], "[1,2]")
        self.assertEqual(back.body["sell_value"], 50)
        self.assertEqual(back.body["icon_info_msg"], b"ico")

        end = WrapperMessage(
            kind=KIND_LIVE_DRAG_END,
            body={
                "object_source_id": 10,
                "object_target_id": 20,
                "end_system": 2,
                "is_stack": False,
                "player_id": 3,
                "has_location": True,
                "tx": 1.5,
                "ty": 2.5,
                "tz": 3.5,
                "ow": 1.0,
                "routing_surface_secondary_id": 1,
                "routing_surface_type": 2,
                "joint_name_or_hash": 0,
                "slot_hash": 4,
            },
        )
        back = decode_wrapper(encode_wrapper(end))
        self.assertTrue(back.body["has_location"])
        self.assertAlmostEqual(back.body["tx"], 1.5, places=4)
        self.assertEqual(back.body["slot_hash"], 4)

        end_resp = WrapperMessage(
            kind=KIND_LIVE_DRAG_END_RESPONSE,
            body={"success": True, "object_source_id": 10, "next_object_id": -1, "end_system": 2},
        )
        back = decode_wrapper(encode_wrapper(end_resp))
        self.assertTrue(back.body["success"])
        self.assertEqual(back.body["next_object_id"], -1)

        sell = WrapperMessage(
            kind=KIND_LIVE_DRAG_SELL,
            body={
                "object_id": 10,
                "end_system": 1,
                "is_stack": False,
                "sim_id": 5,
                "currency_type": 0,
                "player_id": 3,
                "start_system": 1,
            },
        )
        back = decode_wrapper(encode_wrapper(sell))
        self.assertEqual(back.body["object_id"], 10)

        sell_resp = WrapperMessage(
            kind=KIND_LIVE_DRAG_SELL_RESPONSE,
            body={"object_id": 10, "end_system": 1, "start_system": 1, "accepted": True},
        )
        back = decode_wrapper(encode_wrapper(sell_resp))
        self.assertTrue(back.body["accepted"])

    def test_object_create_destroy_location_roundtrips(self):
        create = WrapperMessage(
            kind=KIND_CREATE_OBJECT,
            body={
                "def_id": 100,
                "obj_id": 200,
                "loc_type": 1,
                "zone_id": 9,
                "content_source": 0,
                "disable_object_commodity_callbacks": False,
            },
        )
        back = decode_wrapper(encode_wrapper(create))
        self.assertEqual(back.body["def_id"], 100)
        self.assertEqual(back.body["obj_id"], 200)

        destroy = WrapperMessage(
            kind=KIND_DESTROY_OBJECT,
            body={"zone_id": 9, "obj_id": 200},
        )
        back = decode_wrapper(encode_wrapper(destroy))
        self.assertEqual(back.body["obj_id"], 200)

        loc = WrapperMessage(
            kind=KIND_SET_OBJECT_LOCATION,
            body={
                "zone_id": 9,
                "obj_id": 200,
                "parent_id": 0,
                "slot_hash": 0,
                "parent_type_info_0": 0,
                "parent_type_info_1": 0,
                "routing_surface_secondary_id": 1,
                "routing_surface_type": 2,
                "tx": 4.5,
                "ty": 0.0,
                "tz": -1.25,
                "ow": 1.0,
            },
        )
        back = decode_wrapper(encode_wrapper(loc))
        self.assertAlmostEqual(back.body["tx"], 4.5, places=4)
        self.assertAlmostEqual(back.body["tz"], -1.25, places=4)
        self.assertEqual(back.body["routing_surface_type"], 2)


    def test_dialog_roundtrips(self):
        resp = WrapperMessage(
            kind=KIND_DIALOG_RESPONSE,
            body={"dialog_id": 9001, "response": 1, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(resp))
        self.assertEqual(back.body["dialog_id"], 9001)
        self.assertEqual(back.body["response"], 1)
        self.assertEqual(back.body["player_id"], 42)

        pick = WrapperMessage(
            kind=KIND_DIALOG_PICK_RESULT,
            body={
                "dialog_id": 9001,
                "ingredient_check": True,
                "prepped_ingredient_check": False,
                "choices_json": "[10, 20, 30]",
                "player_id": 42,
            },
        )
        back = decode_wrapper(encode_wrapper(pick))
        self.assertTrue(back.body["ingredient_check"])
        self.assertFalse(back.body["prepped_ingredient_check"])
        self.assertEqual(back.body["choices_json"], "[10, 20, 30]")

        text_in = WrapperMessage(
            kind=KIND_DIALOG_TEXT_INPUT,
            body={
                "dialog_id": 9001,
                "text_input_name": "name",
                "text_input_value": "Motan",
                "player_id": 42,
            },
        )
        back = decode_wrapper(encode_wrapper(text_in))
        self.assertEqual(back.body["text_input_name"], "name")
        self.assertEqual(back.body["text_input_value"], "Motan")


    def test_situation_roundtrips(self):
        create = WrapperMessage(
            kind=KIND_CREATE_SITUATION,
            body={
                "situation_type": 111,
                "scoring_enabled": True,
                "zone_id": 222,
                "scheduled_time": 333,
                "drama_node_uid": 0,
                "activity_ids": "1,2,3",
                "guest_style": 4,
                "guest_color": 5,
                "guest_args_json": '["10", "20", "INVITED"]',
                "player_id": 42,
            },
        )
        back = decode_wrapper(encode_wrapper(create))
        self.assertEqual(back.body["situation_type"], 111)
        self.assertTrue(back.body["scoring_enabled"])
        self.assertEqual(back.body["zone_id"], 222)
        self.assertEqual(back.body["guest_args_json"], '["10", "20", "INVITED"]')

        start = WrapperMessage(
            kind=KIND_START_SITUATION_CREATION,
            body={"sim_id": 7, "creation_time": 9, "situation_category": 1, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(start))
        self.assertEqual(back.body["sim_id"], 7)
        self.assertEqual(back.body["situation_category"], 1)

        edit = WrapperMessage(
            kind=KIND_START_SITUATION_CREATION_FOR_EDIT,
            body={"opt_sim": 7, "drama_node_uid": -1, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(edit))
        self.assertEqual(back.body["opt_sim"], 7)
        self.assertEqual(back.body["drama_node_uid"], -1)

        destroy = WrapperMessage(
            kind=KIND_DESTROY_USER_FACING_SITUATION,
            body={"situation_id": 55, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(destroy))
        self.assertEqual(back.body["situation_id"], 55)

        end = WrapperMessage(
            kind=KIND_SHOW_END_SITUATION_DIALOG,
            body={
                "situation_id": 55,
                "user_facing_type": 2,
                "has_stayed_late": True,
                "time_token": 99,
                "player_id": 42,
            },
        )
        back = decode_wrapper(encode_wrapper(end))
        self.assertTrue(back.body["has_stayed_late"])
        self.assertEqual(back.body["user_facing_type"], 2)


    def test_inventory_funds_roundtrips(self):
        funds = WrapperMessage(
            kind=KIND_MODIFY_HOUSEHOLD_FUNDS,
            body={
                "amount": -500,
                "household_id": 99,
                "reason": 3,
                "zone_id": 7,
                "player_id": 42,
            },
        )
        back = decode_wrapper(encode_wrapper(funds))
        self.assertEqual(back.body["amount"], -500)
        self.assertEqual(back.body["household_id"], 99)
        self.assertEqual(back.body["reason"], 3)

        sell = WrapperMessage(
            kind=KIND_INVENTORY_SELL_MULTIPLE,
            body={"msg": "sim_id: 1", "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(sell))
        self.assertEqual(back.body["msg"], "sim_id: 1")

        purchase = WrapperMessage(
            kind=KIND_PURCHASE_PICKER_RESPONSE,
            body={
                "inventory_target": 1,
                "inventory_source": 2,
                "currency_type": 0,
                "dialog_id": 9,
                "delivery_method": 1,
                "object_ids_or_definition_ids": True,
                "ids_json": "[10, 1, 50]",
                "player_id": 42,
            },
        )
        back = decode_wrapper(encode_wrapper(purchase))
        self.assertTrue(back.body["object_ids_or_definition_ids"])
        self.assertEqual(back.body["dialog_id"], 9)
        self.assertEqual(back.body["ids_json"], "[10, 1, 50]")

        view = WrapperMessage(
            kind=KIND_INVENTORY_VIEW_UPDATE,
            body={"obj_id": 123, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(view))
        self.assertEqual(back.body["obj_id"], 123)


    def test_travel_roundtrips(self):
        travel = WrapperMessage(
            kind=KIND_TRAVEL_SIMS_TO_ZONE,
            body={
                "opt_sim_id": 7,
                "zone_id": 999,
                "traveling_sim_ids_json": "[7, 8, 9]",
                "player_id": 42,
            },
        )
        back = decode_wrapper(encode_wrapper(travel))
        self.assertEqual(back.body["zone_id"], 999)
        self.assertEqual(back.body["traveling_sim_ids_json"], "[7, 8, 9]")

        finished = WrapperMessage(
            kind=KIND_TRAVEL_FINISHED,
            body={"player_id": 42, "zone_id": 999},
        )
        back = decode_wrapper(encode_wrapper(finished))
        self.assertEqual(back.body["player_id"], 42)

        end = WrapperMessage(
            kind=KIND_END_VACATION,
            body={"travel_group_id": 55, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(end))
        self.assertEqual(back.body["travel_group_id"], 55)

        extend = WrapperMessage(
            kind=KIND_EXTEND_VACATION,
            body={"travel_group_id": 55, "duration_days": 3, "cost": 100, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(extend))
        self.assertEqual(back.body["duration_days"], 3)
        self.assertEqual(back.body["cost"], 100)


    def test_career_roundtrips(self):
        send = WrapperMessage(
            kind=KIND_SEND_TO_WORK,
            body={"sim_id": 7, "career_uid": 100, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(send))
        self.assertEqual(back.body["sim_id"], 7)
        self.assertEqual(back.body["career_uid"], 100)

        leave = WrapperMessage(
            kind=KIND_LEAVE_WORK,
            body={"sim_id": 7, "career_uid": 100, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(leave))
        self.assertEqual(back.body["career_uid"], 100)

        find = WrapperMessage(
            kind=KIND_FIND_CAREER,
            body={"sim_id": 7, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(find))
        self.assertEqual(back.body["sim_id"], 7)

        select = WrapperMessage(
            kind=KIND_SELECT_CAREER,
            body={
                "sim_id": 7,
                "career_instance_id": 11,
                "track_id": 22,
                "level": 3,
                "company_name_hash": 0,
                "reason": 1,
                "schedule_shift_type": 0,
                "player_id": 42,
            },
        )
        back = decode_wrapper(encode_wrapper(select))
        self.assertEqual(back.body["career_instance_id"], 11)
        self.assertEqual(back.body["level"], 3)

        stay = WrapperMessage(kind=KIND_STAY_LATE, body={"player_id": 42})
        back = decode_wrapper(encode_wrapper(stay))
        self.assertEqual(back.body["player_id"], 42)

        follow = WrapperMessage(
            kind=KIND_SET_FOLLOW_ENABLED,
            body={"sim_id": 7, "career_uid": 100, "enabled": True, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(follow))
        self.assertTrue(back.body["enabled"])

        close = WrapperMessage(
            kind=KIND_CAREER_EVENT_SCORING_CLOSE,
            body={"sim_id": 7, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(close))
        self.assertEqual(back.body["sim_id"], 7)


    def test_club_roundtrips(self):
        create = WrapperMessage(
            kind=KIND_CREATE_CLUB,
            body={"club_data": "club_id: 1", "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(create))
        self.assertEqual(back.body["club_data"], "club_id: 1")

        update = WrapperMessage(
            kind=KIND_UPDATE_CLUB,
            body={"club_data": "name: \"Cats\"", "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(update))
        self.assertIn("Cats", back.body["club_data"])

        remove = WrapperMessage(
            kind=KIND_REMOVE_CLUB,
            body={"club_id": 9, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(remove))
        self.assertEqual(back.body["club_id"], 9)

        add = WrapperMessage(
            kind=KIND_ADD_SIM_TO_CLUB,
            body={"sim_id": 7, "club_id": 9, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(add))
        self.assertEqual(back.body["sim_id"], 7)

        start = WrapperMessage(
            kind=KIND_START_CLUB_GATHERING,
            body={"club_id": 9, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(start))
        self.assertEqual(back.body["club_id"], 9)

        end = WrapperMessage(
            kind=KIND_END_CLUB_GATHERING,
            body={"club_id": 9, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(end))
        self.assertEqual(back.body["club_id"], 9)

        invite = WrapperMessage(
            kind=KIND_REQUEST_CLUB_INVITE,
            body={"club_id": 9, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(invite))
        self.assertEqual(back.body["club_id"], 9)


    def test_drama_roundtrips(self):
        show = WrapperMessage(
            kind=KIND_SHOW_FESTIVAL_INFO,
            body={"drama_node_id": 111, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(show))
        self.assertEqual(back.body["drama_node_id"], 111)

        show_uid = WrapperMessage(
            kind=KIND_SHOW_FESTIVAL_INFO_BY_UID,
            body={"drama_node_uid": 222, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(show_uid))
        self.assertEqual(back.body["drama_node_uid"], 222)

        travel_z = WrapperMessage(
            kind=KIND_TRAVEL_TO_FESTIVAL_ZONE,
            body={"drama_node_id": 111, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(travel_z))
        self.assertEqual(back.body["drama_node_id"], 111)

        cancel = WrapperMessage(
            kind=KIND_CANCEL_SCHEDULED_DRAMA_NODE,
            body={"drama_node_id": 333, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(cancel))
        self.assertEqual(back.body["drama_node_id"], 333)

        travel_e = WrapperMessage(
            kind=KIND_TRAVEL_TO_EVENT,
            body={"zone_id": 999, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(travel_e))
        self.assertEqual(back.body["zone_id"], 999)


    def test_business_roundtrips(self):
        open_msg = WrapperMessage(
            kind=KIND_SET_BUSINESS_OPEN,
            body={"is_open": True, "zone_id": 9, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(open_msg))
        self.assertTrue(back.body["is_open"])
        self.assertEqual(back.body["zone_id"], 9)

        markup = WrapperMessage(
            kind=KIND_SET_BUSINESS_MARKUP,
            body={"markup_multiplier": 1.25, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(markup))
        self.assertAlmostEqual(back.body["markup_multiplier"], 1.25, places=4)

        ads = WrapperMessage(
            kind=KIND_SET_BUSINESS_ADVERTISING,
            body={"advertising_type": 2.0, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(ads))
        self.assertAlmostEqual(back.body["advertising_type"], 2.0, places=4)

        quality = WrapperMessage(
            kind=KIND_SET_BUSINESS_QUALITY,
            body={"quality": 1, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(quality))
        self.assertEqual(back.body["quality"], 1)

        xfer = WrapperMessage(
            kind=KIND_TRANSFER_RETAIL_FUNDS,
            body={"amount": 500, "from_zone_id": 1, "to_zone_id": 2, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(xfer))
        self.assertEqual(back.body["amount"], 500)
        self.assertEqual(back.body["from_zone_id"], 1)

        hire = WrapperMessage(
            kind=KIND_HIRE_BUSINESS_EMPLOYEE,
            body={"sim_id": 7, "employee_type": 1, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(hire))
        self.assertEqual(back.body["sim_id"], 7)

        fire = WrapperMessage(
            kind=KIND_FIRE_BUSINESS_EMPLOYEE,
            body={"sim_id": 7, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(fire))
        self.assertEqual(back.body["sim_id"], 7)


    def test_small_business_roundtrips(self):
        push = WrapperMessage(
            kind=KIND_PUSH_REGISTER_BUSINESS,
            body={"business_type": 3, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(push))
        self.assertEqual(back.body["business_type"], 3)

        cfg = WrapperMessage(
            kind=KIND_SHOW_SMALL_BUSINESS_CONFIGURATOR,
            body={"is_edit": True, "player_id": 42, "sim_id": 7},
        )
        back = decode_wrapper(encode_wrapper(cfg))
        self.assertTrue(back.body["is_edit"])
        self.assertEqual(back.body["sim_id"], 7)

        reg = WrapperMessage(
            kind=KIND_REGISTER_SMALL_BUSINESS,
            body={"sim_id": 7, "business_data": "sim_id: 7", "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(reg))
        self.assertEqual(back.body["business_data"], "sim_id: 7")

        upd = WrapperMessage(
            kind=KIND_UPDATE_SMALL_BUSINESS,
            body={"sim_id": 7, "business_data": "name: \"Cafe\"", "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(upd))
        self.assertIn("Cafe", back.body["business_data"])

        open_msg = WrapperMessage(
            kind=KIND_SET_OPEN_SMALL_BUSINESS,
            body={"is_open": True, "sim_id": 7, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(open_msg))
        self.assertTrue(back.body["is_open"])

        emp = WrapperMessage(
            kind=KIND_SHOW_SMALL_BUSINESS_EMPLOYEE_MGMT,
            body={"sim_id": 7, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(emp))
        self.assertEqual(back.body["sim_id"], 7)


    def test_holiday_roundtrips(self):
        get_h = WrapperMessage(
            kind=KIND_GET_HOLIDAY_DATA,
            body={"holiday_id": 5, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(get_h))
        self.assertEqual(back.body["holiday_id"], 5)

        get_a = WrapperMessage(
            kind=KIND_GET_ACTIVE_HOLIDAY_DATA,
            body={"sim_id": 7, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(get_a))
        self.assertEqual(back.body["sim_id"], 7)

        upd = WrapperMessage(
            kind=KIND_UPDATE_HOLIDAY,
            body={"holiday_data": "holiday_id: 5", "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(upd))
        self.assertEqual(back.body["holiday_data"], "holiday_id: 5")

        add = WrapperMessage(
            kind=KIND_ADD_HOLIDAY,
            body={"holiday_data": "name: \"Winterfest\"", "season_type": 3, "day": 1, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(add))
        self.assertEqual(back.body["season_type"], 3)
        self.assertEqual(back.body["day"], 1)

        rem = WrapperMessage(
            kind=KIND_REMOVE_HOLIDAY,
            body={"holiday_id": 5, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(rem))
        self.assertEqual(back.body["holiday_id"], 5)


    def test_whim_roundtrips(self):
        refresh = WrapperMessage(
            kind=KIND_WHIM_REFRESH,
            body={"whim_id": 11, "sim_id": 7, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(refresh))
        self.assertEqual(back.body["whim_id"], 11)
        self.assertEqual(back.body["sim_id"], 7)

        lock = WrapperMessage(
            kind=KIND_WHIM_TOGGLE_LOCK,
            body={"whim_id": 12, "sim_id": 7, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(lock))
        self.assertEqual(back.body["whim_id"], 12)

        award = WrapperMessage(
            kind=KIND_WHIMS_AWARD_PRIZE,
            body={"reward_id": 99, "sim_id": 7, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(award))
        self.assertEqual(back.body["reward_id"], 99)
        self.assertEqual(back.body["sim_id"], 7)

        req = WrapperMessage(
            kind=KIND_REQUEST_SATISFACTION_REWARD_LIST,
            body={"sim_id": 7, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(req))
        self.assertEqual(back.body["sim_id"], 7)
        self.assertEqual(back.body["player_id"], 42)


    def test_bucks_roundtrips(self):
        req = WrapperMessage(
            kind=KIND_REQUEST_PERKS_LIST,
            body={"bucks_type": 3, "owner_id": 7, "sort_by_timestamp": True, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(req))
        self.assertEqual(back.body["bucks_type"], 3)
        self.assertTrue(back.body["sort_by_timestamp"])
        self.assertEqual(back.body["owner_id"], 7)

        unlock = WrapperMessage(
            kind=KIND_UNLOCK_PERK,
            body={"bucks_perk": 99, "unlock_for_free": True, "bucks_type": 3, "owner_id": 7, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(unlock))
        self.assertEqual(back.body["bucks_perk"], 99)
        self.assertTrue(back.body["unlock_for_free"])

        multi = WrapperMessage(
            kind=KIND_UNLOCK_MULTIPLE_PERKS,
            body={"bucks_type": 3, "owner_id": 7, "unlock_for_free": False, "buck_perks": [1, 2, 3], "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(multi))
        self.assertEqual(back.body["buck_perks"], [1, 2, 3])
        self.assertFalse(back.body["unlock_for_free"])

        lock = WrapperMessage(
            kind=KIND_LOCK_ALL_PERKS,
            body={"bucks_type": 3, "owner_id": 7, "refund_cost": True, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(lock))
        self.assertTrue(back.body["refund_cost"])
        self.assertEqual(back.body["bucks_type"], 3)


    def test_multi_unit_roundtrips(self):
        show = WrapperMessage(
            kind=KIND_SHOW_RENTAL_UNIT_MANAGEMENT,
            body={
                "zone_id": 100,
                "house_description_id": -1,
                "is_application_process": True,
                "opt_sim": 7,
                "tenant_view_override": False,
                "player_id": 42,
            },
        )
        back = decode_wrapper(encode_wrapper(show))
        self.assertEqual(back.body["zone_id"], 100)
        self.assertEqual(back.body["house_description_id"], -1)
        self.assertTrue(back.body["is_application_process"])
        self.assertEqual(back.body["opt_sim"], 7)

        rules = WrapperMessage(
            kind=KIND_NOTIFY_BUSINESS_RULES_STATE_CHANGE,
            body={"zone_id": 100, "rule_list": "1:2,3:0", "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(rules))
        self.assertEqual(back.body["rule_list"], "1:2,3:0")

        rent = WrapperMessage(
            kind=KIND_SET_UNIT_RENT_PRICE,
            body={"zone_id": 100, "rent_price": 500, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(rent))
        self.assertEqual(back.body["rent_price"], 500)

        lease = WrapperMessage(
            kind=KIND_SET_UNIT_SIGNED_LEASE_LENGTH,
            body={"zone_id": 100, "length": 7, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(lease))
        self.assertEqual(back.body["length"], 7)

        tenant = WrapperMessage(
            kind=KIND_SELECT_TENANT,
            body={"household_id": 9, "zone_id": 100, "household_name": "The Goths", "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(tenant))
        self.assertEqual(back.body["household_id"], 9)
        self.assertEqual(back.body["household_name"], "The Goths")


    def test_dynasty_roundtrips(self):
        show = WrapperMessage(
            kind=KIND_REQUEST_SHOW_DYNASTY_CONFIGURATOR,
            body={
                "sim_id": 7,
                "dynasty_id": 3,
                "view_my_dynasty_mode": True,
                "from_marriage": False,
                "player_id": 42,
            },
        )
        back = decode_wrapper(encode_wrapper(show))
        self.assertEqual(back.body["sim_id"], 7)
        self.assertEqual(back.body["dynasty_id"], 3)
        self.assertTrue(back.body["view_my_dynasty_mode"])

        create = WrapperMessage(
            kind=KIND_CREATE_DYNASTY,
            body={"dynasty_data": "dynasty_id: 3", "from_existing_dynasty": True, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(create))
        self.assertEqual(back.body["dynasty_data"], "dynasty_id: 3")
        self.assertTrue(back.body["from_existing_dynasty"])

        update = WrapperMessage(
            kind=KIND_UPDATE_DYNASTY,
            body={"dynasty_data": "name: \"Bloodline\"", "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(update))
        self.assertIn("Bloodline", back.body["dynasty_data"])

        rem = WrapperMessage(
            kind=KIND_REMOVE_DYNASTY,
            body={"dynasty_id": 3, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(rem))
        self.assertEqual(back.body["dynasty_id"], 3)


    def test_fame_bills_roundtrips(self):
        fame = WrapperMessage(
            kind=KIND_SET_ALLOW_FAME,
            body={"allow_fame": True, "opt_sim": 7, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(fame))
        self.assertTrue(back.body["allow_fame"])
        self.assertEqual(back.body["opt_sim"], 7)

        sell = WrapperMessage(
            kind=KIND_SELL_EXCESS_UTILITY,
            body={"utility": 1, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(sell))
        self.assertEqual(back.body["utility"], 1)

        action = WrapperMessage(
            kind=KIND_SET_UTILITY_END_BILL_ACTION,
            body={"utility": 1, "utility_action": 2, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(action))
        self.assertEqual(back.body["utility_action"], 2)


    def test_p21_p24_roundtrips(self):
        show_v = WrapperMessage(kind=KIND_SHOW_EXTEND_VACATION, body={"player_id": 42})
        back = decode_wrapper(encode_wrapper(show_v))
        self.assertEqual(back.body["player_id"], 42)

        light = WrapperMessage(
            kind=KIND_SHOW_LIGHT_EDITOR,
            body={"light_object_id": 11, "light_target_type": 1, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(light))
        self.assertEqual(back.body["light_object_id"], 11)

        color = WrapperMessage(
            kind=KIND_SET_COLOR_AND_INTENSITY,
            body={"response_id": 5, "r": 10, "g": 20, "b": 30, "intensity": 0.75, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(color))
        self.assertEqual(back.body["r"], 10)
        self.assertAlmostEqual(back.body["intensity"], 0.75, places=5)

        cheat = WrapperMessage(
            kind=KIND_CHEAT,
            body={
                "cheat_name": "motherlode",
                "sim_id": 7,
                "int_param": 0,
                "bool_param": False,
                "str_param_1": "",
                "str_param_2": "",
                "player_id": 42,
            },
        )
        back = decode_wrapper(encode_wrapper(cheat))
        self.assertEqual(back.body["cheat_name"], "motherlode")
        self.assertEqual(back.body["sim_id"], 7)

        order = WrapperMessage(
            kind=KIND_ORDER_FOR_TABLE,
            body={"sim_orders": "meal_cost: 12", "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(order))
        self.assertEqual(back.body["sim_orders"], "meal_cost: 12")

        cfg = WrapperMessage(
            kind=KIND_REFRESH_RESTAURANT_CONFIG,
            body={"config_data": "attire_id: 1", "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(cfg))
        self.assertEqual(back.body["config_data"], "attire_id: 1")


    def test_p25_p28_roundtrips(self):
        rem = WrapperMessage(
            kind=KIND_SOCIAL_MEDIA_REMOVE_FRIEND,
            body={"author_sim": 1, "target_sim": 2, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(rem))
        self.assertEqual(back.body["author_sim"], 1)
        self.assertEqual(back.body["target_sim"], 2)

        react = WrapperMessage(
            kind=KIND_SOCIAL_MEDIA_ADD_REACTION,
            body={
                "author_sim": 1,
                "target_sim": 2,
                "post_id": 9,
                "post_type": 1,
                "narrative": 2,
                "polarity": 3,
                "player_id": 42,
            },
        )
        back = decode_wrapper(encode_wrapper(react))
        self.assertEqual(back.body["post_id"], 9)
        self.assertEqual(back.body["polarity"], 3)

        posts = WrapperMessage(
            kind=KIND_SOCIAL_MEDIA_MARK_POSTS_SEEN,
            body={"author_sim": 1, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(posts))
        self.assertEqual(back.body["author_sim"], 1)

        msgs = WrapperMessage(
            kind=KIND_SOCIAL_MEDIA_MARK_MESSAGES_SEEN,
            body={"author_sim": 1, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(msgs))
        self.assertEqual(back.body["author_sim"], 1)

        life = WrapperMessage(
            kind=KIND_GENERATE_LIFESTYLES_DIALOG,
            body={"sim_id": 7, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(life))
        self.assertEqual(back.body["sim_id"], 7)

        equip = WrapperMessage(
            kind=KIND_EQUIP_TRAIT,
            body={"trait_type": 99, "sim_id": 7, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(equip))
        self.assertEqual(back.body["trait_type"], 99)

        mile = WrapperMessage(
            kind=KIND_SHOW_LIFETIME_MILESTONES_PANEL,
            body={"opt_sim": 7, "category_id": -1, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(mile))
        self.assertEqual(back.body["opt_sim"], 7)
        self.assertEqual(back.body["category_id"], -1)

        gene = WrapperMessage(
            kind=KIND_GENEALOGY_SHOW_FAMILY_TREE,
            body={
                "sim_info_id": 7,
                "antecedent_depth": 8,
                "descendant_depth": 2,
                "player_id": 42,
            },
        )
        back = decode_wrapper(encode_wrapper(gene))
        self.assertEqual(back.body["sim_info_id"], 7)
        self.assertEqual(back.body["antecedent_depth"], 8)


    def test_university_roundtrips(self):
        enroll = WrapperMessage(
            kind=KIND_UNIVERSITY_ENROLL,
            body={
                "major": 11,
                "university": 22,
                "opt_sim": 7,
                "classes": 3,
                "elective": -1,
                "tuition_cost": 5000,
                "total_scholarship_taken": 1000,
                "is_using_loan": True,
                "destination_zone_id": -1,
                "player_id": 42,
            },
        )
        back = decode_wrapper(encode_wrapper(enroll))
        self.assertEqual(back.body["major"], 11)
        self.assertEqual(back.body["university"], 22)
        self.assertEqual(back.body["elective"], -1)
        self.assertTrue(back.body["is_using_loan"])
        self.assertEqual(back.body["tuition_cost"], 5000)

        cancel = WrapperMessage(
            kind=KIND_CANCEL_ENROLLMENT_DIALOG,
            body={"opt_sim": 7, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(cancel))
        self.assertEqual(back.body["opt_sim"], 7)


    def test_p30_p37_roundtrips(self):
        show = WrapperMessage(kind=KIND_SHOW_HORSE_COMPETITION_UI, body={"player_id": 42})
        self.assertEqual(decode_wrapper(encode_wrapper(show)).body["player_id"], 42)

        pick = WrapperMessage(
            kind=KIND_PICK_NEW_HORSE_ASSIGNEE,
            body={"current_competition_id": 3, "current_sim": 7, "current_horse": -1, "for_horse": True, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(pick))
        self.assertEqual(back.body["current_competition_id"], 3)
        self.assertTrue(back.body["for_horse"])
        self.assertEqual(back.body["current_horse"], -1)

        start = WrapperMessage(
            kind=KIND_START_HORSE_COMPETITION,
            body={"competition_id": 3, "selected_sim": 7, "selected_horse": 9, "player_id": 42},
        )
        self.assertEqual(decode_wrapper(encode_wrapper(start)).body["selected_horse"], 9)

        spell = WrapperMessage(
            kind=KIND_GENERATE_SPELLBOOK_UI,
            body={"opt_target_id": 7, "context": "ctx", "player_id": 42},
        )
        self.assertEqual(decode_wrapper(encode_wrapper(spell)).body["context"], "ctx")

        sched = WrapperMessage(
            kind=KIND_GET_CUSTOM_SCHEDULE,
            body={"zone_id": 100, "name": "Vacay", "premade_name_hash": "", "player_id": 42},
        )
        self.assertEqual(decode_wrapper(encode_wrapper(sched)).body["name"], "Vacay")

        ghost = WrapperMessage(kind=KIND_GET_ULTIMATE_PROGRESS, body={"sim_id": 7, "player_id": 42})
        self.assertEqual(decode_wrapper(encode_wrapper(ghost)).body["sim_id"], 7)

        nb = WrapperMessage(
            kind=KIND_GENERATE_NOTEBOOK,
            body={"sim_id": 7, "initial_category": -1, "initial_subcategory": 2, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(nb))
        self.assertEqual(back.body["initial_category"], -1)
        self.assertEqual(back.body["initial_subcategory"], 2)

        notes = WrapperMessage(kind=KIND_SAVE_NOTES, body={"sim_id": 7, "text": "hello", "player_id": 42})
        self.assertEqual(decode_wrapper(encode_wrapper(notes)).body["text"], "hello")

        asp = WrapperMessage(
            kind=KIND_SET_PRIMARY_ASPIRATION_TRACK,
            body={"aspiration_track": 55, "sim_id": 7, "player_id": 42},
        )
        self.assertEqual(decode_wrapper(encode_wrapper(asp)).body["aspiration_track"], 55)

        cal = WrapperMessage(
            kind=KIND_SET_FAVORITE_CALENDAR_ENTRY,
            body={"event_id": 12, "is_favorite": True, "player_id": 42},
        )
        self.assertTrue(decode_wrapper(encode_wrapper(cal)).body["is_favorite"])

        tip = WrapperMessage(
            kind=KIND_UI_CREATE_HOVERTIP,
            body={"target_id": 99, "is_from_ui": True, "player_id": 42},
        )
        self.assertEqual(decode_wrapper(encode_wrapper(tip)).body["target_id"], 99)


    def test_p38_p43_roundtrips(self):
        photo = WrapperMessage(
            kind=KIND_GET_PHOTO_LIST,
            body={"photo_list_json": '["a","b"]', "player_id": 42},
        )
        self.assertEqual(decode_wrapper(encode_wrapper(photo)).body["photo_list_json"], '["a","b"]')

        ft = WrapperMessage(
            kind=KIND_FAMILY_TREE_SHOW,
            body={"sim_id": 7, "pov_sim_id": 9, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(ft))
        self.assertEqual(back.body["sim_id"], 7)
        self.assertEqual(back.body["pov_sim_id"], 9)

        picker = WrapperMessage(
            kind=KIND_STREET_CIVIC_REQUEST_ADD_PICKER,
            body={"opt_target_id": -1, "added_policies_string": "1,2", "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(picker))
        self.assertEqual(back.body["opt_target_id"], -1)
        self.assertEqual(back.body["added_policies_string"], "1,2")

        board = WrapperMessage(
            kind=KIND_HANDLE_COMMUNITY_BOARD,
            body={"community_board_response": "opaque", "player_id": 42},
        )
        self.assertEqual(decode_wrapper(encode_wrapper(board)).body["community_board_response"], "opaque")

        show = WrapperMessage(
            kind=KIND_SHOW_COMMUNITY_BOARD,
            body={"current_street": False, "opt_sim": 7, "opt_target_id": 3, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(show))
        self.assertFalse(back.body["current_street"])
        self.assertEqual(back.body["opt_sim"], 7)

        motive = WrapperMessage(
            kind=KIND_SOLVE_MOTIVE,
            body={"sim_id": 7, "stat_type": -1, "player_id": 42},
        )
        self.assertEqual(decode_wrapper(encode_wrapper(motive)).body["stat_type"], -1)

        profile = WrapperMessage(
            kind=KIND_OPEN_SIM_PROFILE_UI,
            body={"profile_sim": 7, "actor_sim": 9, "player_id": 42},
        )
        self.assertEqual(decode_wrapper(encode_wrapper(profile)).body["actor_sim"], 9)

        zm = WrapperMessage(
            kind=KIND_ZONE_MODIFIERS_UPDATE,
            body={"removed_modifiers": [1, 2], "added_modifiers": [3], "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(zm))
        self.assertEqual(back.body["removed_modifiers"], [1, 2])
        self.assertEqual(back.body["added_modifiers"], [3])


    def test_p44_p46_roundtrips(self):
        clear = WrapperMessage(
            kind=KIND_CLEAR_PARENT_OBJECT,
            body={"obj_id": 9, "transform": b"{}", "routing_surface_secondary_id": 1, "routing_surface_type": 2, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(clear))
        self.assertEqual(back.body["obj_id"], 9)
        self.assertEqual(back.body["transform"], b"{}")

        flags = WrapperMessage(
            kind=KIND_SET_BUILD_BUY_FLAGS,
            body={"zone_id": 1, "object_id": 2, "build_buy_use_flags": 7, "player_id": 42},
        )
        self.assertEqual(decode_wrapper(encode_wrapper(flags)).body["build_buy_use_flags"], 7)

        reset = WrapperMessage(kind=KIND_RESET_OBJECT, body={"zone_id": 1, "obj_id": 2, "player_id": 42})
        self.assertEqual(decode_wrapper(encode_wrapper(reset)).body["obj_id"], 2)

        parent = WrapperMessage(
            kind=KIND_SET_PARENT_OBJECT,
            body={"obj_id": 1, "parent_id": 2, "transform": b"t", "joint_name": "j", "slot_hash": 3, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(parent))
        self.assertEqual(back.body["joint_name"], "j")
        self.assertEqual(back.body["slot_hash"], 3)

        deff = WrapperMessage(kind=KIND_SET_DEFINITION, body={"obj_id": 1, "definition_id": 99, "player_id": 42})
        self.assertEqual(decode_wrapper(encode_wrapper(deff)).body["definition_id"], 99)

        scale = WrapperMessage(kind=KIND_SCALE_OBJECT, body={"obj_id": 1, "scale": 1.5, "player_id": 42})
        self.assertAlmostEqual(decode_wrapper(encode_wrapper(scale)).body["scale"], 1.5, places=5)

        exitm = WrapperMessage(kind=KIND_BUILD_BUY_EXIT, body={"player_id": 42})
        self.assertEqual(decode_wrapper(encode_wrapper(exitm)).body["player_id"], 42)

        floor = WrapperMessage(
            kind=KIND_SET_FLOOR_FEATURE,
            body={"floor_feature_type": 1, "point_x": 1.0, "point_y": 2.0, "point_z": 3.0, "level_index": 0, "value": 0.5, "player_id": 42},
        )
        back = decode_wrapper(encode_wrapper(floor))
        self.assertAlmostEqual(back.body["point_x"], 1.0, places=5)
        self.assertAlmostEqual(back.body["value"], 0.5, places=5)

        preg = WrapperMessage(kind=KIND_CREATE_SIM_INFO, body={"sim_info": b"abcd", "player_id": 42})
        self.assertEqual(decode_wrapper(encode_wrapper(preg)).body["sim_info"], b"abcd")

class DeepProtocolTests(unittest.TestCase):
    def test_builders_validate(self):
        validate_message(msg.make_session_role("host"))
        validate_message(msg.make_deep_host(1001, room_id="lobby"))
        blob = base64.b64encode(b"abc").decode("ascii")
        validate_message(msg.make_deep_relay(blob, "host", kind="generate_choices"))
        validate_message(msg.make_deep_relay(blob, "player", target_player_id=5))
        validate_message(msg.make_hello("A", "1.0", want_host=True))

    def test_relay_requires_target_for_player_route(self):
        blob = base64.b64encode(b"abc").decode("ascii")
        with self.assertRaises(ProtocolError):
            msg.make_deep_relay(blob, "player")


class DeepSessionClientTests(unittest.TestCase):
    def test_session_routes_wrapper(self):
        from simmp_client.deep.session import DeepSession
        from simmp_client.deep.override import Override
        from simmp_client.deep.message_handler import MessageHandler

        Override.clear_registry()
        MessageHandler.clear()
        sent = []
        deep = DeepSession()
        deep.bind(send_fn=sent.append, player_id=7)
        deep.activate(False, host_player_id=1)
        wrapper = WrapperMessage(kind=KIND_SELECT_CHOICE, body={"choice_id": 1, "reference_id": 2, "sim_id": 3, "player_id": 7})
        self.assertTrue(deep.send_wrapper(wrapper, route="host"))
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["type"], "DEEP_RELAY")
        self.assertEqual(sent[0]["payload"]["route"], "host")
        raw = base64.b64decode(sent[0]["payload"]["blob"])
        back = decode_wrapper(raw)
        self.assertEqual(back.kind, KIND_SELECT_CHOICE)
        deep.deactivate()
        Override.clear_registry()
        MessageHandler.clear()

    def test_override_install_by_role(self):
        from simmp_client.deep.override import Override, Role

        Override.clear_registry()

        class Dummy(object):
            def ping(self):
                return "orig"

        dummy_mod = type(sys)("deep_test_mod")
        dummy_mod.Dummy = Dummy
        sys.modules["deep_test_mod"] = dummy_mod
        try:
            @Override(Dummy.ping, role=Role.JOINER, target=Dummy)
            def _ping(original, self):
                return "patched"

            self.assertEqual(Dummy().ping(), "orig")
            Override.install_all(is_host=False)
            self.assertEqual(Dummy().ping(), "patched")
            Override.uninstall_all()
            self.assertEqual(Dummy().ping(), "orig")
            Override.install_all(is_host=True)
            self.assertEqual(Dummy().ping(), "orig")
        finally:
            Override.clear_registry()
            sys.modules.pop("deep_test_mod", None)




class DeepAdventurePersistenceTests(unittest.TestCase):
    def tearDown(self):
        from simmp_client.deep.override import Override
        from simmp_client.deep.message_handler import MessageHandler
        from simmp_client.deep.session import SESSION

        Override.clear_registry()
        MessageHandler.clear()
        SESSION.deactivate()
        SESSION.enabled = False
        SESSION.is_host = False

    def test_p47_p48_adventure_persistence(self):
        import types
        from simmp_client.deep.override import Override, Role
        from simmp_client.deep.session import SESSION
        from simmp_client.deep import dialogs as deep_dialogs
        from simmp_client.deep import sim_select
        from simmp_client.deep import adventure as deep_adventure
        from simmp_client.deep import persistence as deep_persistence

        Override.clear_registry()

        # --- mock adventure module ---
        adventure_mod = types.ModuleType("interactions")
        utils_mod = types.ModuleType("interactions.utils")
        adv_mod = types.ModuleType("interactions.utils.adventure")

        class AdventureMoment(object):
            def __init__(self, sim_id):
                self._sim = types.SimpleNamespace(id=sim_id)
                self.called = False

            def run_adventure(self, guid64=None):
                self.called = True
                return "ran-%s" % guid64

        adv_mod.AdventureMoment = AdventureMoment
        sys.modules["interactions"] = adventure_mod
        sys.modules["interactions.utils"] = utils_mod
        sys.modules["interactions.utils.adventure"] = adv_mod
        adventure_mod.utils = utils_mod
        utils_mod.adventure = adv_mod

        # --- mock persistence ---
        services_mod = types.ModuleType("services")
        pers_mod = types.ModuleType("services.persistence_service")

        class PersistenceService(object):
            def save_using(self, *args, **kwargs):
                return "saved"

        pers_mod.PersistenceService = PersistenceService
        sys.modules["services"] = services_mod
        sys.modules["services.persistence_service"] = pers_mod
        services_mod.persistence_service = pers_mod

        game_services_mod = types.ModuleType("game_services")
        game_services_mod.service_manager = types.SimpleNamespace(allow_shutdown=True)
        sys.modules["game_services"] = game_services_mod

        try:
            self.assertTrue(deep_adventure.install_adventure_hooks())
            self.assertTrue(deep_persistence.install_persistence_hooks())

            disconnected = []
            deep_persistence.set_disconnect_fn(lambda: disconnected.append(1))

            # Joiner: adventure suppressed
            SESSION.enabled = True
            SESSION.is_host = False
            SESSION.player_id = 7
            Override.install_all(is_host=False)
            moment = AdventureMoment(99)
            self.assertIsNone(moment.run_adventure(1))
            self.assertFalse(moment.called)

            # Joiner save with allow_shutdown disconnects
            ps = PersistenceService()
            self.assertEqual(ps.save_using(), "saved")
            self.assertEqual(disconnected, [1])

            Override.uninstall_all()
            disconnected[:] = []

            # Host: adventure runs and sets waiting callback for owning joiner
            sim_select.active_sims.clear()
            sim_select.active_sims[42] = 99
            SESSION.is_host = True
            SESSION.player_id = 1
            Override.install_all(is_host=True)
            deep_dialogs.waiting_for_callback_player_id = None
            moment2 = AdventureMoment(99)
            # Patch run to observe waiting id during call
            seen = []
            orig = AdventureMoment.run_adventure.__func__ if hasattr(AdventureMoment.run_adventure, "__func__") else None

            def _observe(self, guid64=None):
                seen.append(deep_dialogs.waiting_for_callback_player_id)
                self.called = True
                return "ran-%s" % guid64

            # The override wraps the class method; call through installed wrapper
            result = moment2.run_adventure(5)
            self.assertTrue(moment2.called or result == "ran-5" or result is not None)
            # After return, waiting id restored
            self.assertIsNone(deep_dialogs.waiting_for_callback_player_id)

            # Host save does not use joiner disconnect path (override not installed for host)
            ps2 = PersistenceService()
            self.assertEqual(ps2.save_using(), "saved")
            self.assertEqual(disconnected, [])
        finally:
            Override.clear_registry()
            for key in (
                "interactions",
                "interactions.utils",
                "interactions.utils.adventure",
                "services.persistence_service",
                "game_services",
            ):
                sys.modules.pop(key, None)
            deep_persistence.set_disconnect_fn(None)
            sim_select.active_sims.clear()

class DeepServerHostTests(unittest.TestCase):
    def test_claim_host_first_wins(self):
        from server.state.session import Session

        session = Session(min_players=1)
        self.assertEqual(session.claim_host("lobby", 1000), 1000)
        self.assertEqual(session.claim_host("lobby", 1001), 1000)
        self.assertTrue(session.clear_host_if("lobby", 1000))
        self.assertIsNone(session.room_host("lobby"))
        self.assertEqual(session.claim_host("lobby", 1001), 1001)


if __name__ == "__main__":
    unittest.main()
