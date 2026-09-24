"""Deep protobuf message types for Motanplayer host-authoritative relays."""

from simmp.deep import wire

KIND_GAME_NETWORK = "game_network"
KIND_GENERATE_CHOICES = "generate_choices"
KIND_GENERATE_PHONE_CHOICES = "generate_phone_choices"
KIND_SELECT_CHOICE = "select_choice"
KIND_PUSH_INTERACTION = "push_interaction"
KIND_CANCEL_INTERACTION = "cancel_interaction"
KIND_HAS_CHOICES = "has_choices"
KIND_HAS_CHOICES_RESPONSE = "has_choices_response"
KIND_SET_CLOCK_SPEED = "set_clock_speed"
KIND_SET_ACTIVE_SIM = "set_active_sim"
KIND_SET_AUTONOMY_ENABLED = "set_autonomy_enabled"
KIND_LIVE_DRAG_START = "live_drag_start"
KIND_LIVE_DRAG_START_RESPONSE = "live_drag_start_response"
KIND_LIVE_DRAG_END = "live_drag_end"
KIND_LIVE_DRAG_END_RESPONSE = "live_drag_end_response"
KIND_LIVE_DRAG_SELL = "live_drag_sell"
KIND_LIVE_DRAG_SELL_RESPONSE = "live_drag_sell_response"

KIND_CREATE_OBJECT = "create_object"
KIND_DESTROY_OBJECT = "destroy_object"
KIND_SET_OBJECT_LOCATION = "set_object_location"

KIND_DIALOG_RESPONSE = "dialog_response"
KIND_DIALOG_PICK_RESULT = "dialog_pick_result"
KIND_DIALOG_TEXT_INPUT = "dialog_text_input"

KIND_CREATE_SITUATION = "create_situation"
KIND_START_SITUATION_CREATION = "start_situation_creation"
KIND_START_SITUATION_CREATION_FOR_EDIT = "start_situation_creation_for_edit"
KIND_DESTROY_USER_FACING_SITUATION = "destroy_user_facing_situation"
KIND_SHOW_END_SITUATION_DIALOG = "show_end_situation_dialog"

KIND_MODIFY_HOUSEHOLD_FUNDS = "modify_household_funds"
KIND_INVENTORY_SELL_MULTIPLE = "inventory_sell_multiple"
KIND_PURCHASE_PICKER_RESPONSE = "purchase_picker_response"
KIND_INVENTORY_VIEW_UPDATE = "inventory_view_update"

KIND_TRAVEL_SIMS_TO_ZONE = "travel_sims_to_zone"
KIND_TRAVEL_FINISHED = "travel_finished"
KIND_END_VACATION = "end_vacation"
KIND_EXTEND_VACATION = "extend_vacation"

KIND_SEND_TO_WORK = "send_to_work"
KIND_LEAVE_WORK = "leave_work"
KIND_FIND_CAREER = "find_career"
KIND_SELECT_CAREER = "select_career"
KIND_STAY_LATE = "stay_late"
KIND_SET_FOLLOW_ENABLED = "set_follow_enabled"
KIND_CAREER_EVENT_SCORING_CLOSE = "career_event_scoring_close"

KIND_CREATE_CLUB = "create_club"
KIND_UPDATE_CLUB = "update_club"
KIND_REMOVE_CLUB = "remove_club"
KIND_ADD_SIM_TO_CLUB = "add_sim_to_club"
KIND_START_CLUB_GATHERING = "start_club_gathering"
KIND_END_CLUB_GATHERING = "end_club_gathering"
KIND_REQUEST_CLUB_INVITE = "request_club_invite"

KIND_SHOW_FESTIVAL_INFO = "show_festival_info"
KIND_SHOW_FESTIVAL_INFO_BY_UID = "show_festival_info_by_uid"
KIND_TRAVEL_TO_FESTIVAL_ZONE = "travel_to_festival_zone"
KIND_CANCEL_SCHEDULED_DRAMA_NODE = "cancel_scheduled_drama_node"
KIND_TRAVEL_TO_EVENT = "travel_to_event"

KIND_SET_BUSINESS_OPEN = "set_business_open"
KIND_SET_BUSINESS_MARKUP = "set_business_markup"
KIND_SET_BUSINESS_ADVERTISING = "set_business_advertising"
KIND_SET_BUSINESS_QUALITY = "set_business_quality"
KIND_TRANSFER_RETAIL_FUNDS = "transfer_retail_funds"
KIND_HIRE_BUSINESS_EMPLOYEE = "hire_business_employee"
KIND_FIRE_BUSINESS_EMPLOYEE = "fire_business_employee"

KIND_PUSH_REGISTER_BUSINESS = "push_register_business"
KIND_SHOW_SMALL_BUSINESS_CONFIGURATOR = "show_small_business_configurator"
KIND_REGISTER_SMALL_BUSINESS = "register_small_business"
KIND_UPDATE_SMALL_BUSINESS = "update_small_business"
KIND_SET_OPEN_SMALL_BUSINESS = "set_open_small_business"
KIND_SHOW_SMALL_BUSINESS_EMPLOYEE_MGMT = "show_small_business_employee_mgmt"

KIND_GET_HOLIDAY_DATA = "get_holiday_data"
KIND_GET_ACTIVE_HOLIDAY_DATA = "get_active_holiday_data"
KIND_UPDATE_HOLIDAY = "update_holiday"
KIND_ADD_HOLIDAY = "add_holiday"
KIND_REMOVE_HOLIDAY = "remove_holiday"

KIND_WHIM_REFRESH = "whim_refresh"
KIND_WHIM_TOGGLE_LOCK = "whim_toggle_lock"
KIND_WHIMS_AWARD_PRIZE = "whims_award_prize"
KIND_REQUEST_SATISFACTION_REWARD_LIST = "request_satisfaction_reward_list"

KIND_REQUEST_PERKS_LIST = "request_perks_list"
KIND_UNLOCK_PERK = "unlock_perk"
KIND_UNLOCK_MULTIPLE_PERKS = "unlock_multiple_perks"
KIND_LOCK_ALL_PERKS = "lock_all_perks"

KIND_SHOW_RENTAL_UNIT_MANAGEMENT = "show_rental_unit_management"
KIND_NOTIFY_BUSINESS_RULES_STATE_CHANGE = "notify_business_rules_state_change"
KIND_SET_UNIT_RENT_PRICE = "set_unit_rent_price"
KIND_SET_UNIT_SIGNED_LEASE_LENGTH = "set_unit_signed_lease_length"
KIND_SELECT_TENANT = "select_tenant"

KIND_REQUEST_SHOW_DYNASTY_CONFIGURATOR = "request_show_dynasty_configurator"
KIND_CREATE_DYNASTY = "create_dynasty"
KIND_UPDATE_DYNASTY = "update_dynasty"
KIND_REMOVE_DYNASTY = "remove_dynasty"

KIND_SET_ALLOW_FAME = "set_allow_fame"
KIND_SELL_EXCESS_UTILITY = "sell_excess_utility"
KIND_SET_UTILITY_END_BILL_ACTION = "set_utility_end_bill_action"

KIND_SHOW_EXTEND_VACATION = "show_extend_vacation"
KIND_SHOW_LIGHT_EDITOR = "show_light_editor"
KIND_SET_COLOR_AND_INTENSITY = "set_color_and_intensity"
KIND_CHEAT = "cheat"
KIND_ORDER_FOR_TABLE = "order_for_table"
KIND_REFRESH_RESTAURANT_CONFIG = "refresh_restaurant_config"

KIND_SOCIAL_MEDIA_REMOVE_FRIEND = "social_media_remove_friend"
KIND_SOCIAL_MEDIA_ADD_REACTION = "social_media_add_reaction"
KIND_SOCIAL_MEDIA_MARK_POSTS_SEEN = "social_media_mark_posts_seen"
KIND_SOCIAL_MEDIA_MARK_MESSAGES_SEEN = "social_media_mark_messages_seen"
KIND_GENERATE_LIFESTYLES_DIALOG = "generate_lifestyles_dialog"
KIND_EQUIP_TRAIT = "equip_trait"
KIND_SHOW_LIFETIME_MILESTONES_PANEL = "show_lifetime_milestones_panel"
KIND_GENEALOGY_SHOW_FAMILY_TREE = "genealogy_show_family_tree"

KIND_UNIVERSITY_ENROLL = "university_enroll"
KIND_CANCEL_ENROLLMENT_DIALOG = "cancel_enrollment_dialog"

KIND_SHOW_HORSE_COMPETITION_UI = "show_horse_competition_ui"
KIND_PICK_NEW_HORSE_ASSIGNEE = "pick_new_horse_assignee"
KIND_START_HORSE_COMPETITION = "start_horse_competition"
KIND_GENERATE_SPELLBOOK_UI = "generate_spellbook_ui"
KIND_GET_CUSTOM_SCHEDULE = "get_custom_schedule"
KIND_GET_ULTIMATE_PROGRESS = "get_ultimate_progress"
KIND_GENERATE_NOTEBOOK = "generate_notebook"
KIND_SAVE_NOTES = "save_notes"
KIND_SET_PRIMARY_ASPIRATION_TRACK = "set_primary_aspiration_track"
KIND_SET_FAVORITE_CALENDAR_ENTRY = "set_favorite_calendar_entry"
KIND_UI_CREATE_HOVERTIP = "ui_create_hovertip"

KIND_GET_PHOTO_LIST = "get_photo_list"
KIND_FAMILY_TREE_SHOW = "family_tree_show"
KIND_STREET_CIVIC_REQUEST_ADD_PICKER = "street_civic_request_add_picker"
KIND_HANDLE_COMMUNITY_BOARD = "handle_community_board"
KIND_SHOW_COMMUNITY_BOARD = "show_community_board"
KIND_SOLVE_MOTIVE = "solve_motive"
KIND_OPEN_SIM_PROFILE_UI = "open_sim_profile_ui"
KIND_ZONE_MODIFIERS_UPDATE = "zone_modifiers_update"

KIND_CLEAR_PARENT_OBJECT = "clear_parent_object"
KIND_SET_BUILD_BUY_FLAGS = "set_build_buy_flags"
KIND_RESET_OBJECT = "reset_object"
KIND_SET_PARENT_OBJECT = "set_parent_object"
KIND_SET_DEFINITION = "set_definition"
KIND_SCALE_OBJECT = "scale_object"
KIND_BUILD_BUY_EXIT = "build_buy_exit"
KIND_SET_FLOOR_FEATURE = "set_floor_feature"
KIND_CREATE_SIM_INFO = "create_sim_info"

# WrapperMessage field numbers (Motanplayer schema).
_F_TARGET_CLIENT = 1
_F_CLIENT_ID = 2
_F_GAME_NETWORK = 10
_F_GENERATE_CHOICES = 11
_F_GENERATE_PHONE = 12
_F_SELECT_CHOICE = 13
_F_PUSH_INTERACTION = 14
_F_CANCEL_INTERACTION = 15
_F_HAS_CHOICES = 16
_F_HAS_CHOICES_RESPONSE = 17
_F_SET_CLOCK_SPEED = 18
_F_SET_ACTIVE_SIM = 19
_F_SET_AUTONOMY_ENABLED = 20
_F_LIVE_DRAG_START = 21
_F_LIVE_DRAG_START_RESPONSE = 22
_F_LIVE_DRAG_END = 23
_F_LIVE_DRAG_END_RESPONSE = 24
_F_LIVE_DRAG_SELL = 25
_F_LIVE_DRAG_SELL_RESPONSE = 26

_F_CREATE_OBJECT = 27
_F_DESTROY_OBJECT = 28
_F_SET_OBJECT_LOCATION = 29

_F_DIALOG_RESPONSE = 30
_F_DIALOG_PICK_RESULT = 31
_F_DIALOG_TEXT_INPUT = 32

_F_CREATE_SITUATION = 33
_F_START_SITUATION_CREATION = 34
_F_START_SITUATION_CREATION_FOR_EDIT = 35
_F_DESTROY_USER_FACING_SITUATION = 36
_F_SHOW_END_SITUATION_DIALOG = 37

_F_MODIFY_HOUSEHOLD_FUNDS = 38
_F_INVENTORY_SELL_MULTIPLE = 39
_F_PURCHASE_PICKER_RESPONSE = 40
_F_INVENTORY_VIEW_UPDATE = 41

_F_TRAVEL_SIMS_TO_ZONE = 42
_F_TRAVEL_FINISHED = 43
_F_END_VACATION = 44
_F_EXTEND_VACATION = 45

_F_SEND_TO_WORK = 46
_F_LEAVE_WORK = 47
_F_FIND_CAREER = 48
_F_SELECT_CAREER = 49
_F_STAY_LATE = 50
_F_SET_FOLLOW_ENABLED = 51
_F_CAREER_EVENT_SCORING_CLOSE = 52

_F_CREATE_CLUB = 53
_F_UPDATE_CLUB = 54
_F_REMOVE_CLUB = 55
_F_ADD_SIM_TO_CLUB = 56
_F_START_CLUB_GATHERING = 57
_F_END_CLUB_GATHERING = 58
_F_REQUEST_CLUB_INVITE = 59

_F_SHOW_FESTIVAL_INFO = 60
_F_SHOW_FESTIVAL_INFO_BY_UID = 61
_F_TRAVEL_TO_FESTIVAL_ZONE = 62
_F_CANCEL_SCHEDULED_DRAMA_NODE = 63
_F_TRAVEL_TO_EVENT = 64

_F_SET_BUSINESS_OPEN = 65
_F_SET_BUSINESS_MARKUP = 66
_F_SET_BUSINESS_ADVERTISING = 67
_F_SET_BUSINESS_QUALITY = 68
_F_TRANSFER_RETAIL_FUNDS = 69
_F_HIRE_BUSINESS_EMPLOYEE = 70
_F_FIRE_BUSINESS_EMPLOYEE = 71

_F_PUSH_REGISTER_BUSINESS = 72
_F_SHOW_SMALL_BUSINESS_CONFIGURATOR = 73
_F_REGISTER_SMALL_BUSINESS = 74
_F_UPDATE_SMALL_BUSINESS = 75
_F_SET_OPEN_SMALL_BUSINESS = 76
_F_SHOW_SMALL_BUSINESS_EMPLOYEE_MGMT = 77

_F_GET_HOLIDAY_DATA = 78
_F_GET_ACTIVE_HOLIDAY_DATA = 79
_F_UPDATE_HOLIDAY = 80
_F_ADD_HOLIDAY = 81
_F_REMOVE_HOLIDAY = 82

_F_WHIM_REFRESH = 83
_F_WHIM_TOGGLE_LOCK = 84
_F_WHIMS_AWARD_PRIZE = 85
_F_REQUEST_SATISFACTION_REWARD_LIST = 86

_F_REQUEST_PERKS_LIST = 87
_F_UNLOCK_PERK = 88
_F_UNLOCK_MULTIPLE_PERKS = 89
_F_LOCK_ALL_PERKS = 90

_F_SHOW_RENTAL_UNIT_MANAGEMENT = 91
_F_NOTIFY_BUSINESS_RULES_STATE_CHANGE = 92
_F_SET_UNIT_RENT_PRICE = 93
_F_SET_UNIT_SIGNED_LEASE_LENGTH = 94
_F_SELECT_TENANT = 95

_F_REQUEST_SHOW_DYNASTY_CONFIGURATOR = 96
_F_CREATE_DYNASTY = 97
_F_UPDATE_DYNASTY = 98
_F_REMOVE_DYNASTY = 99

_F_SET_ALLOW_FAME = 100
_F_SELL_EXCESS_UTILITY = 101
_F_SET_UTILITY_END_BILL_ACTION = 102

_F_SHOW_EXTEND_VACATION = 103
_F_SHOW_LIGHT_EDITOR = 104
_F_SET_COLOR_AND_INTENSITY = 105
_F_CHEAT = 106
_F_ORDER_FOR_TABLE = 107
_F_REFRESH_RESTAURANT_CONFIG = 108

_F_SOCIAL_MEDIA_REMOVE_FRIEND = 109
_F_SOCIAL_MEDIA_ADD_REACTION = 110
_F_SOCIAL_MEDIA_MARK_POSTS_SEEN = 111
_F_SOCIAL_MEDIA_MARK_MESSAGES_SEEN = 112
_F_GENERATE_LIFESTYLES_DIALOG = 113
_F_EQUIP_TRAIT = 114
_F_SHOW_LIFETIME_MILESTONES_PANEL = 115
_F_GENEALOGY_SHOW_FAMILY_TREE = 116

_F_UNIVERSITY_ENROLL = 117
_F_CANCEL_ENROLLMENT_DIALOG = 118

_F_SHOW_HORSE_COMPETITION_UI = 119
_F_PICK_NEW_HORSE_ASSIGNEE = 120
_F_START_HORSE_COMPETITION = 121
_F_GENERATE_SPELLBOOK_UI = 122
_F_GET_CUSTOM_SCHEDULE = 123
_F_GET_ULTIMATE_PROGRESS = 124
_F_GENERATE_NOTEBOOK = 125
_F_SAVE_NOTES = 126
_F_SET_PRIMARY_ASPIRATION_TRACK = 127
_F_SET_FAVORITE_CALENDAR_ENTRY = 128
_F_UI_CREATE_HOVERTIP = 129

_F_GET_PHOTO_LIST = 130
_F_FAMILY_TREE_SHOW = 131
_F_STREET_CIVIC_REQUEST_ADD_PICKER = 132
_F_HANDLE_COMMUNITY_BOARD = 133
_F_SHOW_COMMUNITY_BOARD = 134
_F_SOLVE_MOTIVE = 135
_F_OPEN_SIM_PROFILE_UI = 136
_F_ZONE_MODIFIERS_UPDATE = 137

_F_CLEAR_PARENT_OBJECT = 138
_F_SET_BUILD_BUY_FLAGS = 139
_F_RESET_OBJECT = 140
_F_SET_PARENT_OBJECT = 141
_F_SET_DEFINITION = 142
_F_SCALE_OBJECT = 143
_F_BUILD_BUY_EXIT = 144
_F_SET_FLOOR_FEATURE = 145
_F_CREATE_SIM_INFO = 146

_KIND_TO_FIELD = {
    KIND_GAME_NETWORK: _F_GAME_NETWORK,
    KIND_GENERATE_CHOICES: _F_GENERATE_CHOICES,
    KIND_GENERATE_PHONE_CHOICES: _F_GENERATE_PHONE,
    KIND_SELECT_CHOICE: _F_SELECT_CHOICE,
    KIND_PUSH_INTERACTION: _F_PUSH_INTERACTION,
    KIND_CANCEL_INTERACTION: _F_CANCEL_INTERACTION,
    KIND_HAS_CHOICES: _F_HAS_CHOICES,
    KIND_HAS_CHOICES_RESPONSE: _F_HAS_CHOICES_RESPONSE,
    KIND_SET_CLOCK_SPEED: _F_SET_CLOCK_SPEED,
    KIND_SET_ACTIVE_SIM: _F_SET_ACTIVE_SIM,
    KIND_SET_AUTONOMY_ENABLED: _F_SET_AUTONOMY_ENABLED,
    KIND_LIVE_DRAG_START: _F_LIVE_DRAG_START,
    KIND_LIVE_DRAG_START_RESPONSE: _F_LIVE_DRAG_START_RESPONSE,
    KIND_LIVE_DRAG_END: _F_LIVE_DRAG_END,
    KIND_LIVE_DRAG_END_RESPONSE: _F_LIVE_DRAG_END_RESPONSE,
    KIND_LIVE_DRAG_SELL: _F_LIVE_DRAG_SELL,
    KIND_LIVE_DRAG_SELL_RESPONSE: _F_LIVE_DRAG_SELL_RESPONSE,

    KIND_CREATE_OBJECT: _F_CREATE_OBJECT,
    KIND_DESTROY_OBJECT: _F_DESTROY_OBJECT,
    KIND_SET_OBJECT_LOCATION: _F_SET_OBJECT_LOCATION,

    KIND_DIALOG_RESPONSE: _F_DIALOG_RESPONSE,
    KIND_DIALOG_PICK_RESULT: _F_DIALOG_PICK_RESULT,
    KIND_DIALOG_TEXT_INPUT: _F_DIALOG_TEXT_INPUT,

    KIND_CREATE_SITUATION: _F_CREATE_SITUATION,
    KIND_START_SITUATION_CREATION: _F_START_SITUATION_CREATION,
    KIND_START_SITUATION_CREATION_FOR_EDIT: _F_START_SITUATION_CREATION_FOR_EDIT,
    KIND_DESTROY_USER_FACING_SITUATION: _F_DESTROY_USER_FACING_SITUATION,
    KIND_SHOW_END_SITUATION_DIALOG: _F_SHOW_END_SITUATION_DIALOG,

    KIND_MODIFY_HOUSEHOLD_FUNDS: _F_MODIFY_HOUSEHOLD_FUNDS,
    KIND_INVENTORY_SELL_MULTIPLE: _F_INVENTORY_SELL_MULTIPLE,
    KIND_PURCHASE_PICKER_RESPONSE: _F_PURCHASE_PICKER_RESPONSE,
    KIND_INVENTORY_VIEW_UPDATE: _F_INVENTORY_VIEW_UPDATE,

    KIND_TRAVEL_SIMS_TO_ZONE: _F_TRAVEL_SIMS_TO_ZONE,
    KIND_TRAVEL_FINISHED: _F_TRAVEL_FINISHED,
    KIND_END_VACATION: _F_END_VACATION,
    KIND_EXTEND_VACATION: _F_EXTEND_VACATION,

    KIND_SEND_TO_WORK: _F_SEND_TO_WORK,
    KIND_LEAVE_WORK: _F_LEAVE_WORK,
    KIND_FIND_CAREER: _F_FIND_CAREER,
    KIND_SELECT_CAREER: _F_SELECT_CAREER,
    KIND_STAY_LATE: _F_STAY_LATE,
    KIND_SET_FOLLOW_ENABLED: _F_SET_FOLLOW_ENABLED,
    KIND_CAREER_EVENT_SCORING_CLOSE: _F_CAREER_EVENT_SCORING_CLOSE,

    KIND_CREATE_CLUB: _F_CREATE_CLUB,
    KIND_UPDATE_CLUB: _F_UPDATE_CLUB,
    KIND_REMOVE_CLUB: _F_REMOVE_CLUB,
    KIND_ADD_SIM_TO_CLUB: _F_ADD_SIM_TO_CLUB,
    KIND_START_CLUB_GATHERING: _F_START_CLUB_GATHERING,
    KIND_END_CLUB_GATHERING: _F_END_CLUB_GATHERING,
    KIND_REQUEST_CLUB_INVITE: _F_REQUEST_CLUB_INVITE,

    KIND_SHOW_FESTIVAL_INFO: _F_SHOW_FESTIVAL_INFO,
    KIND_SHOW_FESTIVAL_INFO_BY_UID: _F_SHOW_FESTIVAL_INFO_BY_UID,
    KIND_TRAVEL_TO_FESTIVAL_ZONE: _F_TRAVEL_TO_FESTIVAL_ZONE,
    KIND_CANCEL_SCHEDULED_DRAMA_NODE: _F_CANCEL_SCHEDULED_DRAMA_NODE,
    KIND_TRAVEL_TO_EVENT: _F_TRAVEL_TO_EVENT,

    KIND_SET_BUSINESS_OPEN: _F_SET_BUSINESS_OPEN,
    KIND_SET_BUSINESS_MARKUP: _F_SET_BUSINESS_MARKUP,
    KIND_SET_BUSINESS_ADVERTISING: _F_SET_BUSINESS_ADVERTISING,
    KIND_SET_BUSINESS_QUALITY: _F_SET_BUSINESS_QUALITY,
    KIND_TRANSFER_RETAIL_FUNDS: _F_TRANSFER_RETAIL_FUNDS,
    KIND_HIRE_BUSINESS_EMPLOYEE: _F_HIRE_BUSINESS_EMPLOYEE,
    KIND_FIRE_BUSINESS_EMPLOYEE: _F_FIRE_BUSINESS_EMPLOYEE,

    KIND_PUSH_REGISTER_BUSINESS: _F_PUSH_REGISTER_BUSINESS,
    KIND_SHOW_SMALL_BUSINESS_CONFIGURATOR: _F_SHOW_SMALL_BUSINESS_CONFIGURATOR,
    KIND_REGISTER_SMALL_BUSINESS: _F_REGISTER_SMALL_BUSINESS,
    KIND_UPDATE_SMALL_BUSINESS: _F_UPDATE_SMALL_BUSINESS,
    KIND_SET_OPEN_SMALL_BUSINESS: _F_SET_OPEN_SMALL_BUSINESS,
    KIND_SHOW_SMALL_BUSINESS_EMPLOYEE_MGMT: _F_SHOW_SMALL_BUSINESS_EMPLOYEE_MGMT,

    KIND_GET_HOLIDAY_DATA: _F_GET_HOLIDAY_DATA,
    KIND_GET_ACTIVE_HOLIDAY_DATA: _F_GET_ACTIVE_HOLIDAY_DATA,
    KIND_UPDATE_HOLIDAY: _F_UPDATE_HOLIDAY,
    KIND_ADD_HOLIDAY: _F_ADD_HOLIDAY,
    KIND_REMOVE_HOLIDAY: _F_REMOVE_HOLIDAY,

    KIND_WHIM_REFRESH: _F_WHIM_REFRESH,
    KIND_WHIM_TOGGLE_LOCK: _F_WHIM_TOGGLE_LOCK,
    KIND_WHIMS_AWARD_PRIZE: _F_WHIMS_AWARD_PRIZE,
    KIND_REQUEST_SATISFACTION_REWARD_LIST: _F_REQUEST_SATISFACTION_REWARD_LIST,

    KIND_REQUEST_PERKS_LIST: _F_REQUEST_PERKS_LIST,
    KIND_UNLOCK_PERK: _F_UNLOCK_PERK,
    KIND_UNLOCK_MULTIPLE_PERKS: _F_UNLOCK_MULTIPLE_PERKS,
    KIND_LOCK_ALL_PERKS: _F_LOCK_ALL_PERKS,

    KIND_SHOW_RENTAL_UNIT_MANAGEMENT: _F_SHOW_RENTAL_UNIT_MANAGEMENT,
    KIND_NOTIFY_BUSINESS_RULES_STATE_CHANGE: _F_NOTIFY_BUSINESS_RULES_STATE_CHANGE,
    KIND_SET_UNIT_RENT_PRICE: _F_SET_UNIT_RENT_PRICE,
    KIND_SET_UNIT_SIGNED_LEASE_LENGTH: _F_SET_UNIT_SIGNED_LEASE_LENGTH,
    KIND_SELECT_TENANT: _F_SELECT_TENANT,

    KIND_REQUEST_SHOW_DYNASTY_CONFIGURATOR: _F_REQUEST_SHOW_DYNASTY_CONFIGURATOR,
    KIND_CREATE_DYNASTY: _F_CREATE_DYNASTY,
    KIND_UPDATE_DYNASTY: _F_UPDATE_DYNASTY,
    KIND_REMOVE_DYNASTY: _F_REMOVE_DYNASTY,

    KIND_SET_ALLOW_FAME: _F_SET_ALLOW_FAME,
    KIND_SELL_EXCESS_UTILITY: _F_SELL_EXCESS_UTILITY,
    KIND_SET_UTILITY_END_BILL_ACTION: _F_SET_UTILITY_END_BILL_ACTION,

    KIND_SHOW_EXTEND_VACATION: _F_SHOW_EXTEND_VACATION,
    KIND_SHOW_LIGHT_EDITOR: _F_SHOW_LIGHT_EDITOR,
    KIND_SET_COLOR_AND_INTENSITY: _F_SET_COLOR_AND_INTENSITY,
    KIND_CHEAT: _F_CHEAT,
    KIND_ORDER_FOR_TABLE: _F_ORDER_FOR_TABLE,
    KIND_REFRESH_RESTAURANT_CONFIG: _F_REFRESH_RESTAURANT_CONFIG,

    KIND_SOCIAL_MEDIA_REMOVE_FRIEND: _F_SOCIAL_MEDIA_REMOVE_FRIEND,
    KIND_SOCIAL_MEDIA_ADD_REACTION: _F_SOCIAL_MEDIA_ADD_REACTION,
    KIND_SOCIAL_MEDIA_MARK_POSTS_SEEN: _F_SOCIAL_MEDIA_MARK_POSTS_SEEN,
    KIND_SOCIAL_MEDIA_MARK_MESSAGES_SEEN: _F_SOCIAL_MEDIA_MARK_MESSAGES_SEEN,
    KIND_GENERATE_LIFESTYLES_DIALOG: _F_GENERATE_LIFESTYLES_DIALOG,
    KIND_EQUIP_TRAIT: _F_EQUIP_TRAIT,
    KIND_SHOW_LIFETIME_MILESTONES_PANEL: _F_SHOW_LIFETIME_MILESTONES_PANEL,
    KIND_GENEALOGY_SHOW_FAMILY_TREE: _F_GENEALOGY_SHOW_FAMILY_TREE,

    KIND_UNIVERSITY_ENROLL: _F_UNIVERSITY_ENROLL,
    KIND_CANCEL_ENROLLMENT_DIALOG: _F_CANCEL_ENROLLMENT_DIALOG,

    KIND_SHOW_HORSE_COMPETITION_UI: _F_SHOW_HORSE_COMPETITION_UI,
    KIND_PICK_NEW_HORSE_ASSIGNEE: _F_PICK_NEW_HORSE_ASSIGNEE,
    KIND_START_HORSE_COMPETITION: _F_START_HORSE_COMPETITION,
    KIND_GENERATE_SPELLBOOK_UI: _F_GENERATE_SPELLBOOK_UI,
    KIND_GET_CUSTOM_SCHEDULE: _F_GET_CUSTOM_SCHEDULE,
    KIND_GET_ULTIMATE_PROGRESS: _F_GET_ULTIMATE_PROGRESS,
    KIND_GENERATE_NOTEBOOK: _F_GENERATE_NOTEBOOK,
    KIND_SAVE_NOTES: _F_SAVE_NOTES,
    KIND_SET_PRIMARY_ASPIRATION_TRACK: _F_SET_PRIMARY_ASPIRATION_TRACK,
    KIND_SET_FAVORITE_CALENDAR_ENTRY: _F_SET_FAVORITE_CALENDAR_ENTRY,
    KIND_UI_CREATE_HOVERTIP: _F_UI_CREATE_HOVERTIP,

    KIND_GET_PHOTO_LIST: _F_GET_PHOTO_LIST,
    KIND_FAMILY_TREE_SHOW: _F_FAMILY_TREE_SHOW,
    KIND_STREET_CIVIC_REQUEST_ADD_PICKER: _F_STREET_CIVIC_REQUEST_ADD_PICKER,
    KIND_HANDLE_COMMUNITY_BOARD: _F_HANDLE_COMMUNITY_BOARD,
    KIND_SHOW_COMMUNITY_BOARD: _F_SHOW_COMMUNITY_BOARD,
    KIND_SOLVE_MOTIVE: _F_SOLVE_MOTIVE,
    KIND_OPEN_SIM_PROFILE_UI: _F_OPEN_SIM_PROFILE_UI,
    KIND_ZONE_MODIFIERS_UPDATE: _F_ZONE_MODIFIERS_UPDATE,

    KIND_CLEAR_PARENT_OBJECT: _F_CLEAR_PARENT_OBJECT,
    KIND_SET_BUILD_BUY_FLAGS: _F_SET_BUILD_BUY_FLAGS,
    KIND_RESET_OBJECT: _F_RESET_OBJECT,
    KIND_SET_PARENT_OBJECT: _F_SET_PARENT_OBJECT,
    KIND_SET_DEFINITION: _F_SET_DEFINITION,
    KIND_SCALE_OBJECT: _F_SCALE_OBJECT,
    KIND_BUILD_BUY_EXIT: _F_BUILD_BUY_EXIT,
    KIND_SET_FLOOR_FEATURE: _F_SET_FLOOR_FEATURE,
    KIND_CREATE_SIM_INFO: _F_CREATE_SIM_INFO,
}

_FIELD_TO_KIND = dict((v, k) for k, v in _KIND_TO_FIELD.items())


class WrapperMessage(object):
    """Envelope for deep command + native game-network traffic."""

    def __init__(self, target_client=0, client_id=0, kind=None, body=None):
        self.target_client = int(target_client or 0)
        self.client_id = int(client_id or 0)
        self.kind = kind
        self.body = body if body is not None else {}

    def encode(self):
        return encode_wrapper(self)


def _encode_game_network(body):
    return wire.encode_message([
        (1, "varint", int(body.get("msg_id", 0))),
        (2, "bytes", body.get("msg") or b""),
    ])


def _decode_game_network(raw):
    out = {"msg_id": 0, "msg": b""}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["msg_id"] = wire.as_varint(value)
        elif number == 2 and wtype == wire.WIRE_LEN:
            out["msg"] = wire.as_bytes(value)
    return out


def _encode_generate_choices(body):
    return wire.encode_message([
        (1, "fixed64", body.get("target_id", 0)),
        (2, "sint64", body.get("pick_type", 0)),
        (3, "float", body.get("x", 0.0)),
        (4, "float", body.get("y", 0.0)),
        (5, "float", body.get("z", 0.0)),
        (6, "fixed64", body.get("lot_id", 0)),
        (7, "sint64", body.get("level", 0)),
        (8, "fixed64", body.get("reference_id", 0)),
        (9, "bool", body.get("is_routable", False)),
        (10, "fixed64", body.get("sim_id", 0)),
        (11, "varint", body.get("player_id", 0)),
        (12, "varint", body.get("shift", 0)),
    ])


def _decode_generate_choices(raw):
    out = {
        "target_id": 0,
        "pick_type": 0,
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
        "lot_id": 0,
        "level": 0,
        "reference_id": 0,
        "is_routable": False,
        "sim_id": 0,
        "player_id": 0,
        "shift": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["target_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["pick_type"] = wire.as_sint(value)
        elif number == 3 and wtype == wire.WIRE_32BIT:
            out["x"] = wire.as_float(value)
        elif number == 4 and wtype == wire.WIRE_32BIT:
            out["y"] = wire.as_float(value)
        elif number == 5 and wtype == wire.WIRE_32BIT:
            out["z"] = wire.as_float(value)
        elif number == 6 and wtype == wire.WIRE_64BIT:
            out["lot_id"] = wire.as_fixed64(value)
        elif number == 7 and wtype == wire.WIRE_VARINT:
            out["level"] = wire.as_sint(value)
        elif number == 8 and wtype == wire.WIRE_64BIT:
            out["reference_id"] = wire.as_fixed64(value)
        elif number == 9 and wtype == wire.WIRE_VARINT:
            out["is_routable"] = wire.as_bool(value)
        elif number == 10 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 11 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
        elif number == 12 and wtype == wire.WIRE_VARINT:
            out["shift"] = wire.as_varint(value)
    return out



def _encode_generate_phone_choices(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "varint", body.get("player_id", 0)),
        (3, "fixed64", body.get("reference_id", 0)),
        (4, "sint64", body.get("selected_affordance_id", -1)),
    ])


def _decode_generate_phone_choices(raw):
    out = {"sim_id": 0, "player_id": 0, "reference_id": 0, "selected_affordance_id": -1}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
        elif number == 3 and wtype == wire.WIRE_64BIT:
            out["reference_id"] = wire.as_fixed64(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["selected_affordance_id"] = wire.as_sint(value)
    return out

def _encode_select_choice(body):
    return wire.encode_message([
        (1, "varint", body.get("choice_id", 0)),
        (2, "fixed64", body.get("reference_id", 0)),
        (3, "fixed64", body.get("sim_id", 0)),
        (4, "varint", body.get("player_id", 0)),
    ])


def _decode_select_choice(raw):
    out = {"choice_id": 0, "reference_id": 0, "sim_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["choice_id"] = wire.as_varint(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["reference_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_push_interaction(body):
    return wire.encode_message([
        (1, "fixed64", body.get("affordance", 0)),
        (2, "sint64", body.get("opt_target", -1)),
        (3, "sint64", body.get("opt_sim", -1)),
        (4, "sint64", body.get("priority", 0)),
        (5, "varint", body.get("player_id", 0)),
    ])


def _decode_push_interaction(raw):
    out = {"affordance": 0, "opt_target": -1, "opt_sim": -1, "priority": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["affordance"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["opt_target"] = wire.as_sint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["opt_sim"] = wire.as_sint(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["priority"] = wire.as_sint(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_cancel_interaction(body):
    return wire.encode_message([
        (1, "fixed64", body.get("interaction_id", 0)),
        (2, "varint", body.get("context_handle", 0)),
        (3, "fixed64", body.get("sim_id", 0)),
        (4, "varint", body.get("player_id", 0)),
    ])


def _decode_cancel_interaction(raw):
    out = {"interaction_id": 0, "context_handle": 0, "sim_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["interaction_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["context_handle"] = wire.as_varint(value)
        elif number == 3 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_has_choices(body):
    return wire.encode_message([
        (1, "fixed64", body.get("target_id", 0)),
        (2, "sint64", body.get("pick_type", 0)),
        (3, "float", body.get("x", 0.0)),
        (4, "float", body.get("y", 0.0)),
        (5, "float", body.get("z", 0.0)),
        (6, "fixed64", body.get("lot_id", 0)),
        (7, "sint64", body.get("level", 0)),
        (8, "bool", body.get("control", False)),
        (9, "bool", body.get("alt", False)),
        (10, "bool", body.get("shift", False)),
        (11, "bool", body.get("is_routable", False)),
        (12, "varint", body.get("player_id", 0)),
        (13, "fixed64", body.get("sim_id", 0)),
    ])


def _decode_has_choices(raw):
    out = {
        "target_id": 0,
        "pick_type": 0,
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
        "lot_id": 0,
        "level": 0,
        "control": False,
        "alt": False,
        "shift": False,
        "is_routable": False,
        "player_id": 0,
        "sim_id": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["target_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["pick_type"] = wire.as_sint(value)
        elif number == 3 and wtype == wire.WIRE_32BIT:
            out["x"] = wire.as_float(value)
        elif number == 4 and wtype == wire.WIRE_32BIT:
            out["y"] = wire.as_float(value)
        elif number == 5 and wtype == wire.WIRE_32BIT:
            out["z"] = wire.as_float(value)
        elif number == 6 and wtype == wire.WIRE_64BIT:
            out["lot_id"] = wire.as_fixed64(value)
        elif number == 7 and wtype == wire.WIRE_VARINT:
            out["level"] = wire.as_sint(value)
        elif number == 8 and wtype == wire.WIRE_VARINT:
            out["control"] = wire.as_bool(value)
        elif number == 9 and wtype == wire.WIRE_VARINT:
            out["alt"] = wire.as_bool(value)
        elif number == 10 and wtype == wire.WIRE_VARINT:
            out["shift"] = wire.as_bool(value)
        elif number == 11 and wtype == wire.WIRE_VARINT:
            out["is_routable"] = wire.as_bool(value)
        elif number == 12 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
        elif number == 13 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
    return out



CLOCK_METHOD_SET = 0
CLOCK_METHOD_PUSH = 1
CLOCK_METHOD_POP = 2


def _encode_set_clock_speed(body):
    return wire.encode_message([
        (1, "varint", body.get("speed", 0)),
        (2, "bool", body.get("immediate", False)),
        (3, "varint", body.get("source", 0)),
        (4, "string", body.get("reason") or ""),
        (5, "varint", body.get("method", CLOCK_METHOD_SET)),
        (6, "varint", body.get("player_id", 0)),
    ])


def _decode_set_clock_speed(raw):
    out = {
        "speed": 0,
        "immediate": False,
        "source": 0,
        "reason": "",
        "method": CLOCK_METHOD_SET,
        "player_id": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["speed"] = wire.as_varint(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["immediate"] = wire.as_bool(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["source"] = wire.as_varint(value)
        elif number == 4 and wtype == wire.WIRE_LEN:
            out["reason"] = wire.as_string(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["method"] = wire.as_varint(value)
        elif number == 6 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_set_active_sim(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_set_active_sim(raw):
    out = {"sim_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_set_autonomy_enabled(body):
    return wire.encode_message([
        (1, "bool", body.get("enabled", False)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_set_autonomy_enabled(raw):
    out = {"enabled": False, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["enabled"] = wire.as_bool(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_live_drag_start(body):
    return wire.encode_message([
        (1, "fixed64", body.get("live_drag_object_id", 0)),
        (2, "varint", body.get("start_system", 0)),
        (3, "bool", body.get("is_stack", False)),
        (4, "bool", body.get("should_send_start_message", True)),
        (5, "varint", body.get("player_id", 0)),
    ])


def _decode_live_drag_start(raw):
    out = {
        "live_drag_object_id": 0,
        "start_system": 0,
        "is_stack": False,
        "should_send_start_message": True,
        "player_id": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["live_drag_object_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["start_system"] = wire.as_varint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["is_stack"] = wire.as_bool(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["should_send_start_message"] = wire.as_bool(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_live_drag_start_response(body):
    return wire.encode_message([
        (1, "fixed64", body.get("live_drag_object_id", 0)),
        (2, "varint", body.get("start_system", 0)),
        (3, "varint", body.get("end_system", 0)),
        (4, "bytes", body.get("icon_info_msg") or b""),
        (5, "string", body.get("valid_drop_object_ids_json") or "[]"),
        (6, "bool", body.get("should_send_start_message", False)),
        (7, "sint64", body.get("valid_stack_id", 0)),
        (8, "sint64", body.get("sell_value", -1)),
        (9, "bool", body.get("cancel", False)),
    ])


def _decode_live_drag_start_response(raw):
    out = {
        "live_drag_object_id": 0,
        "start_system": 0,
        "end_system": 0,
        "icon_info_msg": b"",
        "valid_drop_object_ids_json": "[]",
        "should_send_start_message": False,
        "valid_stack_id": 0,
        "sell_value": -1,
        "cancel": False,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["live_drag_object_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["start_system"] = wire.as_varint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["end_system"] = wire.as_varint(value)
        elif number == 4 and wtype == wire.WIRE_LEN:
            out["icon_info_msg"] = wire.as_bytes(value)
        elif number == 5 and wtype == wire.WIRE_LEN:
            out["valid_drop_object_ids_json"] = wire.as_string(value)
        elif number == 6 and wtype == wire.WIRE_VARINT:
            out["should_send_start_message"] = wire.as_bool(value)
        elif number == 7 and wtype == wire.WIRE_VARINT:
            out["valid_stack_id"] = wire.as_sint(value)
        elif number == 8 and wtype == wire.WIRE_VARINT:
            out["sell_value"] = wire.as_sint(value)
        elif number == 9 and wtype == wire.WIRE_VARINT:
            out["cancel"] = wire.as_bool(value)
    return out


def _encode_live_drag_end(body):
    return wire.encode_message([
        (1, "fixed64", body.get("object_source_id", 0)),
        (2, "fixed64", body.get("object_target_id", 0)),
        (3, "varint", body.get("end_system", 0)),
        (4, "bool", body.get("is_stack", False)),
        (5, "varint", body.get("player_id", 0)),
        (6, "bool", body.get("has_location", False)),
        (7, "float", body.get("tx", 0.0)),
        (8, "float", body.get("ty", 0.0)),
        (9, "float", body.get("tz", 0.0)),
        (10, "float", body.get("ox", 0.0)),
        (11, "float", body.get("oy", 0.0)),
        (12, "float", body.get("oz", 0.0)),
        (13, "float", body.get("ow", 1.0)),
        (14, "sint64", body.get("routing_surface_secondary_id", 0)),
        (15, "sint64", body.get("routing_surface_type", 0)),
        (16, "sint64", body.get("joint_name_or_hash", 0)),
        (17, "varint", body.get("slot_hash", 0)),
    ])


def _decode_live_drag_end(raw):
    out = {
        "object_source_id": 0,
        "object_target_id": 0,
        "end_system": 0,
        "is_stack": False,
        "player_id": 0,
        "has_location": False,
        "tx": 0.0,
        "ty": 0.0,
        "tz": 0.0,
        "ox": 0.0,
        "oy": 0.0,
        "oz": 0.0,
        "ow": 1.0,
        "routing_surface_secondary_id": 0,
        "routing_surface_type": 0,
        "joint_name_or_hash": 0,
        "slot_hash": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["object_source_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["object_target_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["end_system"] = wire.as_varint(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["is_stack"] = wire.as_bool(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
        elif number == 6 and wtype == wire.WIRE_VARINT:
            out["has_location"] = wire.as_bool(value)
        elif number == 7 and wtype == wire.WIRE_32BIT:
            out["tx"] = wire.as_float(value)
        elif number == 8 and wtype == wire.WIRE_32BIT:
            out["ty"] = wire.as_float(value)
        elif number == 9 and wtype == wire.WIRE_32BIT:
            out["tz"] = wire.as_float(value)
        elif number == 10 and wtype == wire.WIRE_32BIT:
            out["ox"] = wire.as_float(value)
        elif number == 11 and wtype == wire.WIRE_32BIT:
            out["oy"] = wire.as_float(value)
        elif number == 12 and wtype == wire.WIRE_32BIT:
            out["oz"] = wire.as_float(value)
        elif number == 13 and wtype == wire.WIRE_32BIT:
            out["ow"] = wire.as_float(value)
        elif number == 14 and wtype == wire.WIRE_VARINT:
            out["routing_surface_secondary_id"] = wire.as_sint(value)
        elif number == 15 and wtype == wire.WIRE_VARINT:
            out["routing_surface_type"] = wire.as_sint(value)
        elif number == 16 and wtype == wire.WIRE_VARINT:
            out["joint_name_or_hash"] = wire.as_sint(value)
        elif number == 17 and wtype == wire.WIRE_VARINT:
            out["slot_hash"] = wire.as_varint(value)
    return out


def _encode_live_drag_end_response(body):
    return wire.encode_message([
        (1, "bool", body.get("success", False)),
        (2, "fixed64", body.get("object_source_id", 0)),
        (3, "sint64", body.get("next_object_id", -1)),
        (4, "varint", body.get("end_system", 0)),
    ])


def _decode_live_drag_end_response(raw):
    out = {"success": False, "object_source_id": 0, "next_object_id": -1, "end_system": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["success"] = wire.as_bool(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["object_source_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["next_object_id"] = wire.as_sint(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["end_system"] = wire.as_varint(value)
    return out


def _encode_live_drag_sell(body):
    return wire.encode_message([
        (1, "fixed64", body.get("object_id", 0)),
        (2, "varint", body.get("end_system", 0)),
        (3, "bool", body.get("is_stack", False)),
        (4, "fixed64", body.get("sim_id", 0)),
        (5, "varint", body.get("currency_type", 0)),
        (6, "varint", body.get("player_id", 0)),
        (7, "varint", body.get("start_system", 0)),
    ])


def _decode_live_drag_sell(raw):
    out = {
        "object_id": 0,
        "end_system": 0,
        "is_stack": False,
        "sim_id": 0,
        "currency_type": 0,
        "player_id": 0,
        "start_system": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["object_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["end_system"] = wire.as_varint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["is_stack"] = wire.as_bool(value)
        elif number == 4 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["currency_type"] = wire.as_varint(value)
        elif number == 6 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
        elif number == 7 and wtype == wire.WIRE_VARINT:
            out["start_system"] = wire.as_varint(value)
    return out


def _encode_live_drag_sell_response(body):
    return wire.encode_message([
        (1, "fixed64", body.get("object_id", 0)),
        (2, "varint", body.get("end_system", 0)),
        (3, "varint", body.get("start_system", 0)),
        (4, "bool", body.get("accepted", False)),
    ])


def _decode_live_drag_sell_response(raw):
    out = {"object_id": 0, "end_system": 0, "start_system": 0, "accepted": False}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["object_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["end_system"] = wire.as_varint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["start_system"] = wire.as_varint(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["accepted"] = wire.as_bool(value)
    return out


def _encode_create_object(body):
    return wire.encode_message([
        (1, "fixed64", body.get("def_id", 0)),
        (2, "fixed64", body.get("obj_id", 0)),
        (3, "sint64", body.get("loc_type", 0)),
        (4, "fixed64", body.get("zone_id", 0)),
        (5, "sint64", body.get("content_source", 0)),
        (6, "bool", body.get("disable_object_commodity_callbacks", False)),
    ])


def _decode_create_object(raw):
    out = {
        "def_id": 0,
        "obj_id": 0,
        "loc_type": 0,
        "zone_id": 0,
        "content_source": 0,
        "disable_object_commodity_callbacks": False,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["def_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["obj_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["loc_type"] = wire.as_sint(value)
        elif number == 4 and wtype == wire.WIRE_64BIT:
            out["zone_id"] = wire.as_fixed64(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["content_source"] = wire.as_sint(value)
        elif number == 6 and wtype == wire.WIRE_VARINT:
            out["disable_object_commodity_callbacks"] = wire.as_bool(value)
    return out


def _encode_destroy_object(body):
    return wire.encode_message([
        (1, "fixed64", body.get("zone_id", 0)),
        (2, "fixed64", body.get("obj_id", 0)),
    ])


def _decode_destroy_object(raw):
    out = {"zone_id": 0, "obj_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["zone_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["obj_id"] = wire.as_fixed64(value)
    return out


def _encode_set_object_location(body):
    return wire.encode_message([
        (1, "fixed64", body.get("zone_id", 0)),
        (2, "fixed64", body.get("obj_id", 0)),
        (3, "fixed64", body.get("parent_id", 0)),
        (4, "fixed64", body.get("slot_hash", 0)),
        (5, "sint64", body.get("parent_type_info_0", 0)),
        (6, "sint64", body.get("parent_type_info_1", 0)),
        (7, "sint64", body.get("routing_surface_secondary_id", 0)),
        (8, "sint64", body.get("routing_surface_type", 0)),
        (9, "float", body.get("tx", 0.0)),
        (10, "float", body.get("ty", 0.0)),
        (11, "float", body.get("tz", 0.0)),
        (12, "float", body.get("ox", 0.0)),
        (13, "float", body.get("oy", 0.0)),
        (14, "float", body.get("oz", 0.0)),
        (15, "float", body.get("ow", 1.0)),
    ])


def _decode_set_object_location(raw):
    out = {
        "zone_id": 0,
        "obj_id": 0,
        "parent_id": 0,
        "slot_hash": 0,
        "parent_type_info_0": 0,
        "parent_type_info_1": 0,
        "routing_surface_secondary_id": 0,
        "routing_surface_type": 0,
        "tx": 0.0,
        "ty": 0.0,
        "tz": 0.0,
        "ox": 0.0,
        "oy": 0.0,
        "oz": 0.0,
        "ow": 1.0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["zone_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["obj_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_64BIT:
            out["parent_id"] = wire.as_fixed64(value)
        elif number == 4 and wtype == wire.WIRE_64BIT:
            out["slot_hash"] = wire.as_fixed64(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["parent_type_info_0"] = wire.as_sint(value)
        elif number == 6 and wtype == wire.WIRE_VARINT:
            out["parent_type_info_1"] = wire.as_sint(value)
        elif number == 7 and wtype == wire.WIRE_VARINT:
            out["routing_surface_secondary_id"] = wire.as_sint(value)
        elif number == 8 and wtype == wire.WIRE_VARINT:
            out["routing_surface_type"] = wire.as_sint(value)
        elif number == 9 and wtype == wire.WIRE_32BIT:
            out["tx"] = wire.as_float(value)
        elif number == 10 and wtype == wire.WIRE_32BIT:
            out["ty"] = wire.as_float(value)
        elif number == 11 and wtype == wire.WIRE_32BIT:
            out["tz"] = wire.as_float(value)
        elif number == 12 and wtype == wire.WIRE_32BIT:
            out["ox"] = wire.as_float(value)
        elif number == 13 and wtype == wire.WIRE_32BIT:
            out["oy"] = wire.as_float(value)
        elif number == 14 and wtype == wire.WIRE_32BIT:
            out["oz"] = wire.as_float(value)
        elif number == 15 and wtype == wire.WIRE_32BIT:
            out["ow"] = wire.as_float(value)
    return out

def _encode_create_situation(body):
    return wire.encode_message([
        (1, "fixed64", body.get("situation_type", 0)),
        (2, "bool", body.get("scoring_enabled", False)),
        (3, "fixed64", body.get("zone_id", 0)),
        (4, "varint", body.get("scheduled_time", 0)),
        (5, "varint", body.get("drama_node_uid", 0)),
        (6, "string", body.get("activity_ids") or ""),
        (7, "varint", body.get("guest_style", 0)),
        (8, "varint", body.get("guest_color", 0)),
        (9, "string", body.get("guest_args_json") or "[]"),
        (10, "varint", body.get("player_id", 0)),
    ])


def _decode_create_situation(raw):
    out = {
        "situation_type": 0,
        "scoring_enabled": False,
        "zone_id": 0,
        "scheduled_time": 0,
        "drama_node_uid": 0,
        "activity_ids": "",
        "guest_style": 0,
        "guest_color": 0,
        "guest_args_json": "[]",
        "player_id": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["situation_type"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["scoring_enabled"] = wire.as_bool(value)
        elif number == 3 and wtype == wire.WIRE_64BIT:
            out["zone_id"] = wire.as_fixed64(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["scheduled_time"] = wire.as_varint(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["drama_node_uid"] = wire.as_varint(value)
        elif number == 6 and wtype == wire.WIRE_LEN:
            out["activity_ids"] = wire.as_string(value)
        elif number == 7 and wtype == wire.WIRE_VARINT:
            out["guest_style"] = wire.as_varint(value)
        elif number == 8 and wtype == wire.WIRE_VARINT:
            out["guest_color"] = wire.as_varint(value)
        elif number == 9 and wtype == wire.WIRE_LEN:
            out["guest_args_json"] = wire.as_string(value)
        elif number == 10 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_start_situation_creation(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "varint", body.get("creation_time", 0)),
        (3, "varint", body.get("situation_category", 0)),
        (4, "varint", body.get("player_id", 0)),
    ])


def _decode_start_situation_creation(raw):
    out = {"sim_id": 0, "creation_time": 0, "situation_category": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["creation_time"] = wire.as_varint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["situation_category"] = wire.as_varint(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_start_situation_creation_for_edit(body):
    return wire.encode_message([
        (1, "sint64", body.get("opt_sim", -1)),
        (2, "sint64", body.get("drama_node_uid", -1)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_start_situation_creation_for_edit(raw):
    out = {"opt_sim": -1, "drama_node_uid": -1, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["opt_sim"] = wire.as_sint(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["drama_node_uid"] = wire.as_sint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_destroy_user_facing_situation(body):
    return wire.encode_message([
        (1, "fixed64", body.get("situation_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_destroy_user_facing_situation(raw):
    out = {"situation_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["situation_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_show_end_situation_dialog(body):
    return wire.encode_message([
        (1, "fixed64", body.get("situation_id", 0)),
        (2, "varint", body.get("user_facing_type", 0)),
        (3, "bool", body.get("has_stayed_late", False)),
        (4, "varint", body.get("time_token", 0)),
        (5, "varint", body.get("player_id", 0)),
    ])


def _decode_show_end_situation_dialog(raw):
    out = {
        "situation_id": 0,
        "user_facing_type": 0,
        "has_stayed_late": False,
        "time_token": 0,
        "player_id": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["situation_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["user_facing_type"] = wire.as_varint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["has_stayed_late"] = wire.as_bool(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["time_token"] = wire.as_varint(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_modify_household_funds(body):
    return wire.encode_message([
        (1, "sint64", body.get("amount", 0)),
        (2, "fixed64", body.get("household_id", 0)),
        (3, "varint", body.get("reason", 0)),
        (4, "fixed64", body.get("zone_id", 0)),
        (5, "varint", body.get("player_id", 0)),
    ])


def _decode_modify_household_funds(raw):
    out = {"amount": 0, "household_id": 0, "reason": 0, "zone_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["amount"] = wire.as_sint(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["household_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["reason"] = wire.as_varint(value)
        elif number == 4 and wtype == wire.WIRE_64BIT:
            out["zone_id"] = wire.as_fixed64(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_inventory_sell_multiple(body):
    return wire.encode_message([
        (1, "string", body.get("msg") or ""),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_inventory_sell_multiple(raw):
    out = {"msg": "", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_LEN:
            out["msg"] = wire.as_string(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_purchase_picker_response(body):
    return wire.encode_message([
        (1, "fixed64", body.get("inventory_target", 0)),
        (2, "fixed64", body.get("inventory_source", 0)),
        (3, "varint", body.get("currency_type", 0)),
        (4, "fixed64", body.get("dialog_id", 0)),
        (5, "varint", body.get("delivery_method", 0)),
        (6, "bool", body.get("object_ids_or_definition_ids", False)),
        (7, "string", body.get("ids_json") or "[]"),
        (8, "varint", body.get("player_id", 0)),
    ])


def _decode_purchase_picker_response(raw):
    out = {
        "inventory_target": 0,
        "inventory_source": 0,
        "currency_type": 0,
        "dialog_id": 0,
        "delivery_method": 0,
        "object_ids_or_definition_ids": False,
        "ids_json": "[]",
        "player_id": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["inventory_target"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["inventory_source"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["currency_type"] = wire.as_varint(value)
        elif number == 4 and wtype == wire.WIRE_64BIT:
            out["dialog_id"] = wire.as_fixed64(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["delivery_method"] = wire.as_varint(value)
        elif number == 6 and wtype == wire.WIRE_VARINT:
            out["object_ids_or_definition_ids"] = wire.as_bool(value)
        elif number == 7 and wtype == wire.WIRE_LEN:
            out["ids_json"] = wire.as_string(value)
        elif number == 8 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_inventory_view_update(body):
    return wire.encode_message([
        (1, "fixed64", body.get("obj_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_inventory_view_update(raw):
    out = {"obj_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["obj_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_travel_sims_to_zone(body):
    return wire.encode_message([
        (1, "sint64", body.get("opt_sim_id", -1)),
        (2, "fixed64", body.get("zone_id", 0)),
        (3, "string", body.get("traveling_sim_ids_json") or "[]"),
        (4, "varint", body.get("player_id", 0)),
    ])


def _decode_travel_sims_to_zone(raw):
    out = {"opt_sim_id": -1, "zone_id": 0, "traveling_sim_ids_json": "[]", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["opt_sim_id"] = wire.as_sint(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["zone_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_LEN:
            out["traveling_sim_ids_json"] = wire.as_string(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_travel_finished(body):
    return wire.encode_message([
        (1, "varint", body.get("player_id", 0)),
        (2, "fixed64", body.get("zone_id", 0)),
    ])


def _decode_travel_finished(raw):
    out = {"player_id": 0, "zone_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["zone_id"] = wire.as_fixed64(value)
    return out


def _encode_end_vacation(body):
    return wire.encode_message([
        (1, "fixed64", body.get("travel_group_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_end_vacation(raw):
    out = {"travel_group_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["travel_group_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_extend_vacation(body):
    return wire.encode_message([
        (1, "fixed64", body.get("travel_group_id", 0)),
        (2, "varint", body.get("duration_days", 0)),
        (3, "sint64", body.get("cost", 0)),
        (4, "varint", body.get("player_id", 0)),
    ])


def _decode_extend_vacation(raw):
    out = {"travel_group_id": 0, "duration_days": 0, "cost": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["travel_group_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["duration_days"] = wire.as_varint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["cost"] = wire.as_sint(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_send_to_work(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "fixed64", body.get("career_uid", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_send_to_work(raw):
    out = {"sim_id": 0, "career_uid": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["career_uid"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_leave_work(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "fixed64", body.get("career_uid", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_leave_work(raw):
    out = {"sim_id": 0, "career_uid": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["career_uid"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_find_career(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_find_career(raw):
    out = {"sim_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_select_career(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "fixed64", body.get("career_instance_id", 0)),
        (3, "fixed64", body.get("track_id", 0)),
        (4, "varint", body.get("level", 0)),
        (5, "varint", body.get("company_name_hash", 0)),
        (6, "varint", body.get("reason", 0)),
        (7, "varint", body.get("schedule_shift_type", 0)),
        (8, "varint", body.get("player_id", 0)),
    ])


def _decode_select_career(raw):
    out = {
        "sim_id": 0,
        "career_instance_id": 0,
        "track_id": 0,
        "level": 0,
        "company_name_hash": 0,
        "reason": 0,
        "schedule_shift_type": 0,
        "player_id": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["career_instance_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_64BIT:
            out["track_id"] = wire.as_fixed64(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["level"] = wire.as_varint(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["company_name_hash"] = wire.as_varint(value)
        elif number == 6 and wtype == wire.WIRE_VARINT:
            out["reason"] = wire.as_varint(value)
        elif number == 7 and wtype == wire.WIRE_VARINT:
            out["schedule_shift_type"] = wire.as_varint(value)
        elif number == 8 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_stay_late(body):
    return wire.encode_message([
        (1, "varint", body.get("player_id", 0)),
    ])


def _decode_stay_late(raw):
    out = {"player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_set_follow_enabled(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "fixed64", body.get("career_uid", 0)),
        (3, "bool", body.get("enabled", False)),
        (4, "varint", body.get("player_id", 0)),
    ])


def _decode_set_follow_enabled(raw):
    out = {"sim_id": 0, "career_uid": 0, "enabled": False, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["career_uid"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["enabled"] = wire.as_bool(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_career_event_scoring_close(body):
    return wire.encode_message([
        (1, "sint64", body.get("sim_id", -1)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_career_event_scoring_close(raw):
    out = {"sim_id": -1, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["sim_id"] = wire.as_sint(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_create_club(body):
    return wire.encode_message([
        (1, "string", body.get("club_data") or ""),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_create_club(raw):
    out = {"club_data": "", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_LEN:
            out["club_data"] = wire.as_string(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_update_club(body):
    return wire.encode_message([
        (1, "string", body.get("club_data") or ""),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_update_club(raw):
    out = {"club_data": "", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_LEN:
            out["club_data"] = wire.as_string(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_remove_club(body):
    return wire.encode_message([
        (1, "fixed64", body.get("club_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_remove_club(raw):
    out = {"club_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["club_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_add_sim_to_club(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "fixed64", body.get("club_id", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_add_sim_to_club(raw):
    out = {"sim_id": 0, "club_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["club_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_start_club_gathering(body):
    return wire.encode_message([
        (1, "fixed64", body.get("club_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_start_club_gathering(raw):
    out = {"club_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["club_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_end_club_gathering(body):
    return wire.encode_message([
        (1, "fixed64", body.get("club_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_end_club_gathering(raw):
    out = {"club_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["club_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_request_club_invite(body):
    return wire.encode_message([
        (1, "fixed64", body.get("club_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_request_club_invite(raw):
    out = {"club_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["club_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_show_festival_info(body):
    return wire.encode_message([
        (1, "fixed64", body.get("drama_node_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_show_festival_info(raw):
    out = {"drama_node_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["drama_node_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_show_festival_info_by_uid(body):
    return wire.encode_message([
        (1, "fixed64", body.get("drama_node_uid", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_show_festival_info_by_uid(raw):
    out = {"drama_node_uid": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["drama_node_uid"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_travel_to_festival_zone(body):
    return wire.encode_message([
        (1, "fixed64", body.get("drama_node_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_travel_to_festival_zone(raw):
    out = {"drama_node_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["drama_node_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_cancel_scheduled_drama_node(body):
    return wire.encode_message([
        (1, "fixed64", body.get("drama_node_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_cancel_scheduled_drama_node(raw):
    out = {"drama_node_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["drama_node_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_travel_to_event(body):
    return wire.encode_message([
        (1, "fixed64", body.get("zone_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_travel_to_event(raw):
    out = {"zone_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["zone_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_set_business_open(body):
    return wire.encode_message([
        (1, "bool", body.get("is_open", False)),
        (2, "fixed64", body.get("zone_id", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_set_business_open(raw):
    out = {"is_open": False, "zone_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["is_open"] = wire.as_bool(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["zone_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_set_business_markup(body):
    return wire.encode_message([
        (1, "float", float(body.get("markup_multiplier", 0.0))),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_set_business_markup(raw):
    out = {"markup_multiplier": 0.0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_32BIT:
            out["markup_multiplier"] = wire.as_float(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_set_business_advertising(body):
    return wire.encode_message([
        (1, "float", float(body.get("advertising_type", 0.0))),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_set_business_advertising(raw):
    out = {"advertising_type": 0.0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_32BIT:
            out["advertising_type"] = wire.as_float(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_set_business_quality(body):
    return wire.encode_message([
        (1, "varint", body.get("quality", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_set_business_quality(raw):
    out = {"quality": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["quality"] = wire.as_varint(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_transfer_retail_funds(body):
    return wire.encode_message([
        (1, "varint", body.get("amount", 0)),
        (2, "fixed64", body.get("from_zone_id", 0)),
        (3, "fixed64", body.get("to_zone_id", 0)),
        (4, "varint", body.get("player_id", 0)),
    ])


def _decode_transfer_retail_funds(raw):
    out = {"amount": 0, "from_zone_id": 0, "to_zone_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["amount"] = wire.as_varint(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["from_zone_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_64BIT:
            out["to_zone_id"] = wire.as_fixed64(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_hire_business_employee(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "varint", body.get("employee_type", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_hire_business_employee(raw):
    out = {"sim_id": 0, "employee_type": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["employee_type"] = wire.as_varint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_fire_business_employee(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_fire_business_employee(raw):
    out = {"sim_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_push_register_business(body):
    return wire.encode_message([
        (1, "varint", body.get("business_type", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_push_register_business(raw):
    out = {"business_type": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["business_type"] = wire.as_varint(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_show_small_business_configurator(body):
    return wire.encode_message([
        (1, "bool", body.get("is_edit", False)),
        (2, "varint", body.get("player_id", 0)),
        (3, "fixed64", body.get("sim_id", 0)),
    ])


def _decode_show_small_business_configurator(raw):
    out = {"is_edit": False, "player_id": 0, "sim_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["is_edit"] = wire.as_bool(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
        elif number == 3 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
    return out


def _encode_register_small_business(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "string", body.get("business_data") or ""),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_register_small_business(raw):
    out = {"sim_id": 0, "business_data": "", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_LEN:
            out["business_data"] = wire.as_string(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_update_small_business(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "string", body.get("business_data") or ""),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_update_small_business(raw):
    out = {"sim_id": 0, "business_data": "", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_LEN:
            out["business_data"] = wire.as_string(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_set_open_small_business(body):
    return wire.encode_message([
        (1, "bool", body.get("is_open", False)),
        (2, "fixed64", body.get("sim_id", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_set_open_small_business(raw):
    out = {"is_open": False, "sim_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["is_open"] = wire.as_bool(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_show_small_business_employee_mgmt(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_show_small_business_employee_mgmt(raw):
    out = {"sim_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_get_holiday_data(body):
    return wire.encode_message([
        (1, "fixed64", body.get("holiday_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_get_holiday_data(raw):
    out = {"holiday_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["holiday_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_get_active_holiday_data(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_get_active_holiday_data(raw):
    out = {"sim_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_update_holiday(body):
    return wire.encode_message([
        (1, "string", body.get("holiday_data") or ""),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_update_holiday(raw):
    out = {"holiday_data": "", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_LEN:
            out["holiday_data"] = wire.as_string(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_add_holiday(body):
    return wire.encode_message([
        (1, "string", body.get("holiday_data") or ""),
        (2, "varint", body.get("season_type", 0)),
        (3, "varint", body.get("day", 0)),
        (4, "varint", body.get("player_id", 0)),
    ])


def _decode_add_holiday(raw):
    out = {"holiday_data": "", "season_type": 0, "day": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_LEN:
            out["holiday_data"] = wire.as_string(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["season_type"] = wire.as_varint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["day"] = wire.as_varint(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_remove_holiday(body):
    return wire.encode_message([
        (1, "fixed64", body.get("holiday_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_remove_holiday(raw):
    out = {"holiday_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["holiday_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_show_horse_competition_ui(body):
    return wire.encode_message([(1, "varint", body.get("player_id", 0))])

def _decode_show_horse_competition_ui(raw):
    out = {"player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_pick_new_horse_assignee(body):
    return wire.encode_message([
        (1, "fixed64", body.get("current_competition_id", 0)),
        (2, "sint64", body.get("current_sim", -1)),
        (3, "sint64", body.get("current_horse", -1)),
        (4, "bool", body.get("for_horse", False)),
        (5, "varint", body.get("player_id", 0)),
    ])

def _decode_pick_new_horse_assignee(raw):
    out = {"current_competition_id": 0, "current_sim": -1, "current_horse": -1, "for_horse": False, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["current_competition_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["current_sim"] = wire.as_sint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["current_horse"] = wire.as_sint(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["for_horse"] = wire.as_bool(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_start_horse_competition(body):
    return wire.encode_message([
        (1, "fixed64", body.get("competition_id", 0)),
        (2, "sint64", body.get("selected_sim", 0)),
        (3, "sint64", body.get("selected_horse", 0)),
        (4, "varint", body.get("player_id", 0)),
    ])

def _decode_start_horse_competition(raw):
    out = {"competition_id": 0, "selected_sim": 0, "selected_horse": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["competition_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["selected_sim"] = wire.as_sint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["selected_horse"] = wire.as_sint(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_generate_spellbook_ui(body):
    return wire.encode_message([
        (1, "fixed64", body.get("opt_target_id", 0)),
        (2, "string", body.get("context", "") or ""),
        (3, "varint", body.get("player_id", 0)),
    ])

def _decode_generate_spellbook_ui(raw):
    out = {"opt_target_id": 0, "context": "", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["opt_target_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_LEN:
            out["context"] = wire.as_string(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_get_custom_schedule(body):
    return wire.encode_message([
        (1, "fixed64", body.get("zone_id", 0)),
        (2, "string", body.get("name", "") or ""),
        (3, "string", body.get("premade_name_hash", "") or ""),
        (4, "varint", body.get("player_id", 0)),
    ])

def _decode_get_custom_schedule(raw):
    out = {"zone_id": 0, "name": "", "premade_name_hash": "", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["zone_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_LEN:
            out["name"] = wire.as_string(value)
        elif number == 3 and wtype == wire.WIRE_LEN:
            out["premade_name_hash"] = wire.as_string(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_get_ultimate_progress(body):
    return wire.encode_message([
        (1, "sint64", body.get("sim_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])

def _decode_get_ultimate_progress(raw):
    out = {"sim_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["sim_id"] = wire.as_sint(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_generate_notebook(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "sint64", body.get("initial_category", -1)),
        (3, "sint64", body.get("initial_subcategory", -1)),
        (4, "varint", body.get("player_id", 0)),
    ])

def _decode_generate_notebook(raw):
    out = {"sim_id": 0, "initial_category": -1, "initial_subcategory": -1, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["initial_category"] = wire.as_sint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["initial_subcategory"] = wire.as_sint(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_save_notes(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "string", body.get("text", "") or ""),
        (3, "varint", body.get("player_id", 0)),
    ])

def _decode_save_notes(raw):
    out = {"sim_id": 0, "text": "", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_LEN:
            out["text"] = wire.as_string(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_set_primary_aspiration_track(body):
    return wire.encode_message([
        (1, "sint64", body.get("aspiration_track", 0)),
        (2, "fixed64", body.get("sim_id", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])

def _decode_set_primary_aspiration_track(raw):
    out = {"aspiration_track": 0, "sim_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["aspiration_track"] = wire.as_sint(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_set_favorite_calendar_entry(body):
    return wire.encode_message([
        (1, "fixed64", body.get("event_id", 0)),
        (2, "bool", body.get("is_favorite", False)),
        (3, "varint", body.get("player_id", 0)),
    ])

def _decode_set_favorite_calendar_entry(raw):
    out = {"event_id": 0, "is_favorite": False, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["event_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["is_favorite"] = wire.as_bool(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_ui_create_hovertip(body):
    return wire.encode_message([
        (1, "fixed64", body.get("target_id", 0)),
        (2, "bool", body.get("is_from_ui", False)),
        (3, "varint", body.get("player_id", 0)),
    ])

def _decode_ui_create_hovertip(raw):
    out = {"target_id": 0, "is_from_ui": False, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["target_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["is_from_ui"] = wire.as_bool(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_get_photo_list(body):
    return wire.encode_message([
        (1, "string", body.get("photo_list_json") or "[]"),
        (2, "varint", body.get("player_id", 0)),
    ])

def _decode_get_photo_list(raw):
    out = {"photo_list_json": "[]", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_LEN:
            out["photo_list_json"] = wire.as_string(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_family_tree_show(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "fixed64", body.get("pov_sim_id", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])

def _decode_family_tree_show(raw):
    out = {"sim_id": 0, "pov_sim_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["pov_sim_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_street_civic_request_add_picker(body):
    return wire.encode_message([
        (1, "sint64", body.get("opt_target_id", -1)),
        (2, "string", body.get("added_policies_string") or ""),
        (3, "varint", body.get("player_id", 0)),
    ])

def _decode_street_civic_request_add_picker(raw):
    out = {"opt_target_id": -1, "added_policies_string": "", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["opt_target_id"] = wire.as_sint(value)
        elif number == 2 and wtype == wire.WIRE_LEN:
            out["added_policies_string"] = wire.as_string(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_handle_community_board(body):
    return wire.encode_message([
        (1, "string", body.get("community_board_response") or ""),
        (2, "varint", body.get("player_id", 0)),
    ])

def _decode_handle_community_board(raw):
    out = {"community_board_response": "", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_LEN:
            out["community_board_response"] = wire.as_string(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_show_community_board(body):
    return wire.encode_message([
        (1, "bool", body.get("current_street", True)),
        (2, "sint64", body.get("opt_sim", 0)),
        (3, "fixed64", body.get("opt_target_id", 0)),
        (4, "varint", body.get("player_id", 0)),
    ])

def _decode_show_community_board(raw):
    out = {"current_street": True, "opt_sim": 0, "opt_target_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["current_street"] = wire.as_bool(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["opt_sim"] = wire.as_sint(value)
        elif number == 3 and wtype == wire.WIRE_64BIT:
            out["opt_target_id"] = wire.as_fixed64(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_solve_motive(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "sint64", body.get("stat_type", -1)),
        (3, "varint", body.get("player_id", 0)),
    ])

def _decode_solve_motive(raw):
    out = {"sim_id": 0, "stat_type": -1, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["stat_type"] = wire.as_sint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_open_sim_profile_ui(body):
    return wire.encode_message([
        (1, "sint64", body.get("profile_sim", 0)),
        (2, "sint64", body.get("actor_sim", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])

def _decode_open_sim_profile_ui(raw):
    out = {"profile_sim": 0, "actor_sim": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["profile_sim"] = wire.as_sint(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["actor_sim"] = wire.as_sint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_zone_modifiers_update(body):
    fields = [(3, "varint", body.get("player_id", 0))]
    for mid in body.get("removed_modifiers") or []:
        fields.append((1, "fixed64", int(mid)))
    for mid in body.get("added_modifiers") or []:
        fields.append((2, "fixed64", int(mid)))
    return wire.encode_message(fields)

def _decode_zone_modifiers_update(raw):
    out = {"removed_modifiers": [], "added_modifiers": [], "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["removed_modifiers"].append(wire.as_fixed64(value))
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["added_modifiers"].append(wire.as_fixed64(value))
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_university_enroll(body):
    return wire.encode_message([
        (1, "sint64", body.get("major", 0)),
        (2, "sint64", body.get("university", 0)),
        (3, "sint64", body.get("opt_sim", 0)),
        (4, "sint64", body.get("classes", 0)),
        (5, "sint64", body.get("elective", -1)),
        (6, "fixed64", body.get("tuition_cost", 0)),
        (7, "fixed64", body.get("total_scholarship_taken", 0)),
        (8, "bool", body.get("is_using_loan", False)),
        (9, "sint64", body.get("destination_zone_id", -1)),
        (10, "varint", body.get("player_id", 0)),
    ])


def _decode_university_enroll(raw):
    out = {
        "major": 0,
        "university": 0,
        "opt_sim": 0,
        "classes": 0,
        "elective": -1,
        "tuition_cost": 0,
        "total_scholarship_taken": 0,
        "is_using_loan": False,
        "destination_zone_id": -1,
        "player_id": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["major"] = wire.as_sint(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["university"] = wire.as_sint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["opt_sim"] = wire.as_sint(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["classes"] = wire.as_sint(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["elective"] = wire.as_sint(value)
        elif number == 6 and wtype == wire.WIRE_64BIT:
            out["tuition_cost"] = wire.as_fixed64(value)
        elif number == 7 and wtype == wire.WIRE_64BIT:
            out["total_scholarship_taken"] = wire.as_fixed64(value)
        elif number == 8 and wtype == wire.WIRE_VARINT:
            out["is_using_loan"] = wire.as_bool(value)
        elif number == 9 and wtype == wire.WIRE_VARINT:
            out["destination_zone_id"] = wire.as_sint(value)
        elif number == 10 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_cancel_enrollment_dialog(body):
    return wire.encode_message([
        (1, "sint64", body.get("opt_sim", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_cancel_enrollment_dialog(raw):
    out = {"opt_sim": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["opt_sim"] = wire.as_sint(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_social_media_remove_friend(body):
    return wire.encode_message([
        (1, "fixed64", body.get("author_sim", 0)),
        (2, "fixed64", body.get("target_sim", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_social_media_remove_friend(raw):
    out = {"author_sim": 0, "target_sim": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["author_sim"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["target_sim"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_social_media_add_reaction(body):
    return wire.encode_message([
        (1, "fixed64", body.get("author_sim", 0)),
        (2, "fixed64", body.get("target_sim", 0)),
        (3, "fixed64", body.get("post_id", 0)),
        (4, "fixed64", body.get("post_type", 0)),
        (5, "fixed64", body.get("narrative", 0)),
        (6, "fixed64", body.get("polarity", 0)),
        (7, "varint", body.get("player_id", 0)),
    ])


def _decode_social_media_add_reaction(raw):
    out = {
        "author_sim": 0,
        "target_sim": 0,
        "post_id": 0,
        "post_type": 0,
        "narrative": 0,
        "polarity": 0,
        "player_id": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["author_sim"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["target_sim"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_64BIT:
            out["post_id"] = wire.as_fixed64(value)
        elif number == 4 and wtype == wire.WIRE_64BIT:
            out["post_type"] = wire.as_fixed64(value)
        elif number == 5 and wtype == wire.WIRE_64BIT:
            out["narrative"] = wire.as_fixed64(value)
        elif number == 6 and wtype == wire.WIRE_64BIT:
            out["polarity"] = wire.as_fixed64(value)
        elif number == 7 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_social_media_mark_posts_seen(body):
    return wire.encode_message([
        (1, "fixed64", body.get("author_sim", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_social_media_mark_posts_seen(raw):
    out = {"author_sim": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["author_sim"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_social_media_mark_messages_seen(body):
    return wire.encode_message([
        (1, "fixed64", body.get("author_sim", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_social_media_mark_messages_seen(raw):
    out = {"author_sim": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["author_sim"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_generate_lifestyles_dialog(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_generate_lifestyles_dialog(raw):
    out = {"sim_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_equip_trait(body):
    return wire.encode_message([
        (1, "fixed64", body.get("trait_type", 0)),
        (2, "fixed64", body.get("sim_id", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_equip_trait(raw):
    out = {"trait_type": 0, "sim_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["trait_type"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_show_lifetime_milestones_panel(body):
    return wire.encode_message([
        (1, "sint64", body.get("opt_sim", -1)),
        (2, "sint64", body.get("category_id", -1)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_show_lifetime_milestones_panel(raw):
    out = {"opt_sim": -1, "category_id": -1, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["opt_sim"] = wire.as_sint(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["category_id"] = wire.as_sint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_genealogy_show_family_tree(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_info_id", 0)),
        (2, "varint", body.get("antecedent_depth", 0)),
        (3, "varint", body.get("descendant_depth", 0)),
        (4, "varint", body.get("player_id", 0)),
    ])


def _decode_genealogy_show_family_tree(raw):
    out = {"sim_info_id": 0, "antecedent_depth": 0, "descendant_depth": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_info_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["antecedent_depth"] = wire.as_varint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["descendant_depth"] = wire.as_varint(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_show_extend_vacation(body):
    return wire.encode_message([
        (1, "varint", body.get("player_id", 0)),
    ])


def _decode_show_extend_vacation(raw):
    out = {"player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_show_light_editor(body):
    return wire.encode_message([
        (1, "fixed64", body.get("light_object_id", 0)),
        (2, "varint", body.get("light_target_type", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_show_light_editor(raw):
    out = {"light_object_id": 0, "light_target_type": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["light_object_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["light_target_type"] = wire.as_varint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_set_color_and_intensity(body):
    return wire.encode_message([
        (1, "fixed64", body.get("response_id", 0)),
        (2, "varint", body.get("r", 0)),
        (3, "varint", body.get("g", 0)),
        (4, "varint", body.get("b", 0)),
        (5, "float", body.get("intensity", 0.0)),
        (6, "varint", body.get("player_id", 0)),
    ])


def _decode_set_color_and_intensity(raw):
    out = {"response_id": 0, "r": 0, "g": 0, "b": 0, "intensity": 0.0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["response_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["r"] = wire.as_varint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["g"] = wire.as_varint(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["b"] = wire.as_varint(value)
        elif number == 5 and wtype == wire.WIRE_32BIT:
            out["intensity"] = wire.as_float(value)
        elif number == 6 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_cheat(body):
    return wire.encode_message([
        (1, "string", body.get("cheat_name", "") or ""),
        (2, "sint64", body.get("sim_id", 0)),
        (3, "fixed64", body.get("int_param", 0)),
        (4, "bool", body.get("bool_param", False)),
        (5, "string", body.get("str_param_1", "") or ""),
        (6, "string", body.get("str_param_2", "") or ""),
        (7, "varint", body.get("player_id", 0)),
    ])


def _decode_cheat(raw):
    out = {
        "cheat_name": "",
        "sim_id": 0,
        "int_param": 0,
        "bool_param": False,
        "str_param_1": "",
        "str_param_2": "",
        "player_id": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_LEN:
            out["cheat_name"] = wire.as_string(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["sim_id"] = wire.as_sint(value)
        elif number == 3 and wtype == wire.WIRE_64BIT:
            out["int_param"] = wire.as_fixed64(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["bool_param"] = wire.as_bool(value)
        elif number == 5 and wtype == wire.WIRE_LEN:
            out["str_param_1"] = wire.as_string(value)
        elif number == 6 and wtype == wire.WIRE_LEN:
            out["str_param_2"] = wire.as_string(value)
        elif number == 7 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_order_for_table(body):
    return wire.encode_message([
        (1, "string", body.get("sim_orders", "") or ""),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_order_for_table(raw):
    out = {"sim_orders": "", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_LEN:
            out["sim_orders"] = wire.as_string(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_refresh_restaurant_config(body):
    return wire.encode_message([
        (1, "string", body.get("config_data", "") or ""),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_refresh_restaurant_config(raw):
    out = {"config_data": "", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_LEN:
            out["config_data"] = wire.as_string(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_set_allow_fame(body):
    return wire.encode_message([
        (1, "bool", body.get("allow_fame", False)),
        (2, "sint64", body.get("opt_sim", -1)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_set_allow_fame(raw):
    out = {"allow_fame": False, "opt_sim": -1, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["allow_fame"] = wire.as_bool(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["opt_sim"] = wire.as_sint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_sell_excess_utility(body):
    return wire.encode_message([
        (1, "varint", body.get("utility", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_sell_excess_utility(raw):
    out = {"utility": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["utility"] = wire.as_varint(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_set_utility_end_bill_action(body):
    return wire.encode_message([
        (1, "varint", body.get("utility", 0)),
        (2, "varint", body.get("utility_action", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_set_utility_end_bill_action(raw):
    out = {"utility": 0, "utility_action": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["utility"] = wire.as_varint(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["utility_action"] = wire.as_varint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_request_show_dynasty_configurator(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "fixed64", body.get("dynasty_id", 0)),
        (3, "bool", body.get("view_my_dynasty_mode", False)),
        (4, "bool", body.get("from_marriage", False)),
        (5, "varint", body.get("player_id", 0)),
    ])


def _decode_request_show_dynasty_configurator(raw):
    out = {
        "sim_id": 0,
        "dynasty_id": 0,
        "view_my_dynasty_mode": False,
        "from_marriage": False,
        "player_id": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["dynasty_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["view_my_dynasty_mode"] = wire.as_bool(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["from_marriage"] = wire.as_bool(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_create_dynasty(body):
    return wire.encode_message([
        (1, "string", body.get("dynasty_data", "") or ""),
        (2, "bool", body.get("from_existing_dynasty", False)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_create_dynasty(raw):
    out = {"dynasty_data": "", "from_existing_dynasty": False, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_LEN:
            out["dynasty_data"] = wire.as_string(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["from_existing_dynasty"] = wire.as_bool(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_update_dynasty(body):
    return wire.encode_message([
        (1, "string", body.get("dynasty_data", "") or ""),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_update_dynasty(raw):
    out = {"dynasty_data": "", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_LEN:
            out["dynasty_data"] = wire.as_string(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_remove_dynasty(body):
    return wire.encode_message([
        (1, "fixed64", body.get("dynasty_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_remove_dynasty(raw):
    out = {"dynasty_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["dynasty_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_show_rental_unit_management(body):
    return wire.encode_message([
        (1, "sint64", body.get("zone_id", 0)),
        (2, "sint64", body.get("house_description_id", -1)),
        (3, "bool", body.get("is_application_process", False)),
        (4, "sint64", body.get("opt_sim", -1)),
        (5, "bool", body.get("tenant_view_override", False)),
        (6, "varint", body.get("player_id", 0)),
    ])


def _decode_show_rental_unit_management(raw):
    out = {
        "zone_id": 0,
        "house_description_id": -1,
        "is_application_process": False,
        "opt_sim": -1,
        "tenant_view_override": False,
        "player_id": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["zone_id"] = wire.as_sint(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["house_description_id"] = wire.as_sint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["is_application_process"] = wire.as_bool(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["opt_sim"] = wire.as_sint(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["tenant_view_override"] = wire.as_bool(value)
        elif number == 6 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_notify_business_rules_state_change(body):
    return wire.encode_message([
        (1, "sint64", body.get("zone_id", 0)),
        (2, "string", body.get("rule_list", "") or ""),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_notify_business_rules_state_change(raw):
    out = {"zone_id": 0, "rule_list": "", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["zone_id"] = wire.as_sint(value)
        elif number == 2 and wtype == wire.WIRE_LEN:
            out["rule_list"] = wire.as_string(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_set_unit_rent_price(body):
    return wire.encode_message([
        (1, "sint64", body.get("zone_id", 0)),
        (2, "fixed64", body.get("rent_price", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_set_unit_rent_price(raw):
    out = {"zone_id": 0, "rent_price": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["zone_id"] = wire.as_sint(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["rent_price"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_set_unit_signed_lease_length(body):
    return wire.encode_message([
        (1, "sint64", body.get("zone_id", 0)),
        (2, "fixed64", body.get("length", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_set_unit_signed_lease_length(raw):
    out = {"zone_id": 0, "length": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["zone_id"] = wire.as_sint(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["length"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_select_tenant(body):
    return wire.encode_message([
        (1, "fixed64", body.get("household_id", 0)),
        (2, "sint64", body.get("zone_id", 0)),
        (3, "string", body.get("household_name", "") or ""),
        (4, "varint", body.get("player_id", 0)),
    ])


def _decode_select_tenant(raw):
    out = {"household_id": 0, "zone_id": 0, "household_name": "", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["household_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["zone_id"] = wire.as_sint(value)
        elif number == 3 and wtype == wire.WIRE_LEN:
            out["household_name"] = wire.as_string(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_request_perks_list(body):
    return wire.encode_message([
        (1, "varint", body.get("bucks_type", 0)),
        (2, "fixed64", body.get("owner_id", 0)),
        (3, "bool", body.get("sort_by_timestamp", False)),
        (4, "varint", body.get("player_id", 0)),
    ])


def _decode_request_perks_list(raw):
    out = {"bucks_type": 0, "owner_id": 0, "sort_by_timestamp": False, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["bucks_type"] = wire.as_varint(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["owner_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["sort_by_timestamp"] = wire.as_bool(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_unlock_perk(body):
    return wire.encode_message([
        (1, "fixed64", body.get("bucks_perk", 0)),
        (2, "bool", body.get("unlock_for_free", False)),
        (3, "varint", body.get("bucks_type", 0)),
        (4, "fixed64", body.get("owner_id", 0)),
        (5, "varint", body.get("player_id", 0)),
    ])


def _decode_unlock_perk(raw):
    out = {
        "bucks_perk": 0,
        "unlock_for_free": False,
        "bucks_type": 0,
        "owner_id": 0,
        "player_id": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["bucks_perk"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["unlock_for_free"] = wire.as_bool(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["bucks_type"] = wire.as_varint(value)
        elif number == 4 and wtype == wire.WIRE_64BIT:
            out["owner_id"] = wire.as_fixed64(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_unlock_multiple_perks(body):
    fields = [
        (1, "varint", body.get("bucks_type", 0)),
        (2, "fixed64", body.get("owner_id", 0)),
        (3, "bool", body.get("unlock_for_free", False)),
        (5, "varint", body.get("player_id", 0)),
    ]
    for perk_id in body.get("buck_perks") or []:
        fields.append((4, "fixed64", int(perk_id)))
    return wire.encode_message(fields)


def _decode_unlock_multiple_perks(raw):
    out = {
        "bucks_type": 0,
        "owner_id": 0,
        "unlock_for_free": False,
        "buck_perks": [],
        "player_id": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["bucks_type"] = wire.as_varint(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["owner_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["unlock_for_free"] = wire.as_bool(value)
        elif number == 4 and wtype == wire.WIRE_64BIT:
            out["buck_perks"].append(wire.as_fixed64(value))
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_lock_all_perks(body):
    return wire.encode_message([
        (1, "varint", body.get("bucks_type", 0)),
        (2, "fixed64", body.get("owner_id", 0)),
        (3, "bool", body.get("refund_cost", False)),
        (4, "varint", body.get("player_id", 0)),
    ])


def _decode_lock_all_perks(raw):
    out = {"bucks_type": 0, "owner_id": 0, "refund_cost": False, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["bucks_type"] = wire.as_varint(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["owner_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["refund_cost"] = wire.as_bool(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_whim_refresh(body):
    return wire.encode_message([
        (1, "fixed64", body.get("whim_id", 0)),
        (2, "fixed64", body.get("sim_id", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_whim_refresh(raw):
    out = {"whim_id": 0, "sim_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["whim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_whim_toggle_lock(body):
    return wire.encode_message([
        (1, "fixed64", body.get("whim_id", 0)),
        (2, "fixed64", body.get("sim_id", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_whim_toggle_lock(raw):
    out = {"whim_id": 0, "sim_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["whim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_whims_award_prize(body):
    return wire.encode_message([
        (1, "fixed64", body.get("reward_id", 0)),
        (2, "fixed64", body.get("sim_id", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_whims_award_prize(raw):
    out = {"reward_id": 0, "sim_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["reward_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_request_satisfaction_reward_list(body):
    return wire.encode_message([
        (1, "fixed64", body.get("sim_id", 0)),
        (2, "varint", body.get("player_id", 0)),
    ])


def _decode_request_satisfaction_reward_list(raw):
    out = {"sim_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["sim_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_dialog_response(body):
    return wire.encode_message([
        (1, "fixed64", body.get("dialog_id", 0)),
        (2, "sint64", body.get("response", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])


def _decode_dialog_response(raw):
    out = {"dialog_id": 0, "response": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["dialog_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["response"] = wire.as_sint(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_dialog_pick_result(body):
    return wire.encode_message([
        (1, "fixed64", body.get("dialog_id", 0)),
        (2, "bool", body.get("ingredient_check", False)),
        (3, "bool", body.get("prepped_ingredient_check", False)),
        (4, "string", body.get("choices_json") or "[]"),
        (5, "varint", body.get("player_id", 0)),
    ])


def _decode_dialog_pick_result(raw):
    out = {
        "dialog_id": 0,
        "ingredient_check": False,
        "prepped_ingredient_check": False,
        "choices_json": "[]",
        "player_id": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["dialog_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["ingredient_check"] = wire.as_bool(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["prepped_ingredient_check"] = wire.as_bool(value)
        elif number == 4 and wtype == wire.WIRE_LEN:
            out["choices_json"] = wire.as_string(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


def _encode_dialog_text_input(body):
    return wire.encode_message([
        (1, "fixed64", body.get("dialog_id", 0)),
        (2, "string", body.get("text_input_name") or ""),
        (3, "string", body.get("text_input_value") or ""),
        (4, "varint", body.get("player_id", 0)),
    ])


def _decode_dialog_text_input(raw):
    out = {
        "dialog_id": 0,
        "text_input_name": "",
        "text_input_value": "",
        "player_id": 0,
    }
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["dialog_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_LEN:
            out["text_input_name"] = wire.as_string(value)
        elif number == 3 and wtype == wire.WIRE_LEN:
            out["text_input_value"] = wire.as_string(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_has_choices_response(body):
    return wire.encode_message([
        (1, "bool", body.get("immediate", False)),
        (2, "bytes", body.get("msg") or b""),
    ])


def _decode_has_choices_response(raw):
    out = {"immediate": False, "msg": b""}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["immediate"] = wire.as_bool(value)
        elif number == 2 and wtype == wire.WIRE_LEN:
            out["msg"] = wire.as_bytes(value)
    return out



def _encode_clear_parent_object(body):
    return wire.encode_message([
        (1, "fixed64", body.get("obj_id", 0)),
        (2, "bytes", body.get("transform") or b""),
        (3, "sint64", body.get("routing_surface_secondary_id", 0)),
        (4, "sint64", body.get("routing_surface_type", 0)),
        (5, "varint", body.get("player_id", 0)),
    ])

def _decode_clear_parent_object(raw):
    out = {"obj_id": 0, "transform": b"", "routing_surface_secondary_id": 0, "routing_surface_type": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["obj_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_LEN:
            out["transform"] = wire.as_bytes(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["routing_surface_secondary_id"] = wire.as_sint(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["routing_surface_type"] = wire.as_sint(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_set_build_buy_flags(body):
    return wire.encode_message([
        (1, "fixed64", body.get("zone_id", 0)),
        (2, "fixed64", body.get("object_id", 0)),
        (3, "varint", body.get("build_buy_use_flags", 0)),
        (4, "varint", body.get("player_id", 0)),
    ])

def _decode_set_build_buy_flags(raw):
    out = {"zone_id": 0, "object_id": 0, "build_buy_use_flags": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["zone_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["object_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["build_buy_use_flags"] = wire.as_varint(value)
        elif number == 4 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_reset_object(body):
    return wire.encode_message([
        (1, "fixed64", body.get("zone_id", 0)),
        (2, "fixed64", body.get("obj_id", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])

def _decode_reset_object(raw):
    out = {"zone_id": 0, "obj_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["zone_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["obj_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_set_parent_object(body):
    return wire.encode_message([
        (1, "fixed64", body.get("obj_id", 0)),
        (2, "fixed64", body.get("parent_id", 0)),
        (3, "bytes", body.get("transform") or b""),
        (4, "string", body.get("joint_name") or ""),
        (5, "varint", body.get("slot_hash", 0)),
        (6, "varint", body.get("player_id", 0)),
    ])

def _decode_set_parent_object(raw):
    out = {"obj_id": 0, "parent_id": 0, "transform": b"", "joint_name": "", "slot_hash": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["obj_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["parent_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_LEN:
            out["transform"] = wire.as_bytes(value)
        elif number == 4 and wtype == wire.WIRE_LEN:
            out["joint_name"] = wire.as_string(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["slot_hash"] = wire.as_varint(value)
        elif number == 6 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_set_definition(body):
    return wire.encode_message([
        (1, "fixed64", body.get("obj_id", 0)),
        (2, "fixed64", body.get("definition_id", 0)),
        (3, "varint", body.get("player_id", 0)),
    ])

def _decode_set_definition(raw):
    out = {"obj_id": 0, "definition_id": 0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["obj_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_64BIT:
            out["definition_id"] = wire.as_fixed64(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_scale_object(body):
    return wire.encode_message([
        (1, "fixed64", body.get("obj_id", 0)),
        (2, "float", body.get("scale", 1.0)),
        (3, "varint", body.get("player_id", 0)),
    ])

def _decode_scale_object(raw):
    out = {"obj_id": 0, "scale": 1.0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_64BIT:
            out["obj_id"] = wire.as_fixed64(value)
        elif number == 2 and wtype == wire.WIRE_32BIT:
            out["scale"] = wire.as_float(value)
        elif number == 3 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_build_buy_exit(body):
    return wire.encode_message([
        (1, "varint", body.get("player_id", 0)),
    ])

def _decode_build_buy_exit(raw):
    out = {"player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_set_floor_feature(body):
    return wire.encode_message([
        (1, "sint64", body.get("floor_feature_type", 0)),
        (2, "float", body.get("point_x", 0.0)),
        (3, "float", body.get("point_y", 0.0)),
        (4, "float", body.get("point_z", 0.0)),
        (5, "sint64", body.get("level_index", 0)),
        (6, "float", body.get("value", 0.0)),
        (7, "varint", body.get("player_id", 0)),
    ])

def _decode_set_floor_feature(raw):
    out = {"floor_feature_type": 0, "point_x": 0.0, "point_y": 0.0, "point_z": 0.0, "level_index": 0, "value": 0.0, "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_VARINT:
            out["floor_feature_type"] = wire.as_sint(value)
        elif number == 2 and wtype == wire.WIRE_32BIT:
            out["point_x"] = wire.as_float(value)
        elif number == 3 and wtype == wire.WIRE_32BIT:
            out["point_y"] = wire.as_float(value)
        elif number == 4 and wtype == wire.WIRE_32BIT:
            out["point_z"] = wire.as_float(value)
        elif number == 5 and wtype == wire.WIRE_VARINT:
            out["level_index"] = wire.as_sint(value)
        elif number == 6 and wtype == wire.WIRE_32BIT:
            out["value"] = wire.as_float(value)
        elif number == 7 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out

def _encode_create_sim_info(body):
    return wire.encode_message([
        (1, "bytes", body.get("sim_info") or b""),
        (2, "varint", body.get("player_id", 0)),
    ])

def _decode_create_sim_info(raw):
    out = {"sim_info": b"", "player_id": 0}
    for number, wtype, value in wire.decode_fields(raw):
        if number == 1 and wtype == wire.WIRE_LEN:
            out["sim_info"] = wire.as_bytes(value)
        elif number == 2 and wtype == wire.WIRE_VARINT:
            out["player_id"] = wire.as_varint(value)
    return out


_ENCODERS = {
    KIND_GAME_NETWORK: _encode_game_network,
    KIND_GENERATE_CHOICES: _encode_generate_choices,
    KIND_GENERATE_PHONE_CHOICES: _encode_generate_phone_choices,
    KIND_SELECT_CHOICE: _encode_select_choice,
    KIND_PUSH_INTERACTION: _encode_push_interaction,
    KIND_CANCEL_INTERACTION: _encode_cancel_interaction,
    KIND_HAS_CHOICES: _encode_has_choices,
    KIND_HAS_CHOICES_RESPONSE: _encode_has_choices_response,
    KIND_SET_CLOCK_SPEED: _encode_set_clock_speed,
    KIND_SET_ACTIVE_SIM: _encode_set_active_sim,
    KIND_SET_AUTONOMY_ENABLED: _encode_set_autonomy_enabled,
    KIND_LIVE_DRAG_START: _encode_live_drag_start,
    KIND_LIVE_DRAG_START_RESPONSE: _encode_live_drag_start_response,
    KIND_LIVE_DRAG_END: _encode_live_drag_end,
    KIND_LIVE_DRAG_END_RESPONSE: _encode_live_drag_end_response,
    KIND_LIVE_DRAG_SELL: _encode_live_drag_sell,
    KIND_LIVE_DRAG_SELL_RESPONSE: _encode_live_drag_sell_response,

    KIND_CREATE_OBJECT: _encode_create_object,
    KIND_DESTROY_OBJECT: _encode_destroy_object,
    KIND_SET_OBJECT_LOCATION: _encode_set_object_location,

    KIND_DIALOG_RESPONSE: _encode_dialog_response,
    KIND_DIALOG_PICK_RESULT: _encode_dialog_pick_result,
    KIND_DIALOG_TEXT_INPUT: _encode_dialog_text_input,

    KIND_CREATE_SITUATION: _encode_create_situation,
    KIND_START_SITUATION_CREATION: _encode_start_situation_creation,
    KIND_START_SITUATION_CREATION_FOR_EDIT: _encode_start_situation_creation_for_edit,
    KIND_DESTROY_USER_FACING_SITUATION: _encode_destroy_user_facing_situation,
    KIND_SHOW_END_SITUATION_DIALOG: _encode_show_end_situation_dialog,

    KIND_MODIFY_HOUSEHOLD_FUNDS: _encode_modify_household_funds,
    KIND_INVENTORY_SELL_MULTIPLE: _encode_inventory_sell_multiple,
    KIND_PURCHASE_PICKER_RESPONSE: _encode_purchase_picker_response,
    KIND_INVENTORY_VIEW_UPDATE: _encode_inventory_view_update,

    KIND_TRAVEL_SIMS_TO_ZONE: _encode_travel_sims_to_zone,
    KIND_TRAVEL_FINISHED: _encode_travel_finished,
    KIND_END_VACATION: _encode_end_vacation,
    KIND_EXTEND_VACATION: _encode_extend_vacation,

    KIND_SEND_TO_WORK: _encode_send_to_work,
    KIND_LEAVE_WORK: _encode_leave_work,
    KIND_FIND_CAREER: _encode_find_career,
    KIND_SELECT_CAREER: _encode_select_career,
    KIND_STAY_LATE: _encode_stay_late,
    KIND_SET_FOLLOW_ENABLED: _encode_set_follow_enabled,
    KIND_CAREER_EVENT_SCORING_CLOSE: _encode_career_event_scoring_close,

    KIND_CREATE_CLUB: _encode_create_club,
    KIND_UPDATE_CLUB: _encode_update_club,
    KIND_REMOVE_CLUB: _encode_remove_club,
    KIND_ADD_SIM_TO_CLUB: _encode_add_sim_to_club,
    KIND_START_CLUB_GATHERING: _encode_start_club_gathering,
    KIND_END_CLUB_GATHERING: _encode_end_club_gathering,
    KIND_REQUEST_CLUB_INVITE: _encode_request_club_invite,

    KIND_SHOW_FESTIVAL_INFO: _encode_show_festival_info,
    KIND_SHOW_FESTIVAL_INFO_BY_UID: _encode_show_festival_info_by_uid,
    KIND_TRAVEL_TO_FESTIVAL_ZONE: _encode_travel_to_festival_zone,
    KIND_CANCEL_SCHEDULED_DRAMA_NODE: _encode_cancel_scheduled_drama_node,
    KIND_TRAVEL_TO_EVENT: _encode_travel_to_event,

    KIND_SET_BUSINESS_OPEN: _encode_set_business_open,
    KIND_SET_BUSINESS_MARKUP: _encode_set_business_markup,
    KIND_SET_BUSINESS_ADVERTISING: _encode_set_business_advertising,
    KIND_SET_BUSINESS_QUALITY: _encode_set_business_quality,
    KIND_TRANSFER_RETAIL_FUNDS: _encode_transfer_retail_funds,
    KIND_HIRE_BUSINESS_EMPLOYEE: _encode_hire_business_employee,
    KIND_FIRE_BUSINESS_EMPLOYEE: _encode_fire_business_employee,

    KIND_PUSH_REGISTER_BUSINESS: _encode_push_register_business,
    KIND_SHOW_SMALL_BUSINESS_CONFIGURATOR: _encode_show_small_business_configurator,
    KIND_REGISTER_SMALL_BUSINESS: _encode_register_small_business,
    KIND_UPDATE_SMALL_BUSINESS: _encode_update_small_business,
    KIND_SET_OPEN_SMALL_BUSINESS: _encode_set_open_small_business,
    KIND_SHOW_SMALL_BUSINESS_EMPLOYEE_MGMT: _encode_show_small_business_employee_mgmt,

    KIND_GET_HOLIDAY_DATA: _encode_get_holiday_data,
    KIND_GET_ACTIVE_HOLIDAY_DATA: _encode_get_active_holiday_data,
    KIND_UPDATE_HOLIDAY: _encode_update_holiday,
    KIND_ADD_HOLIDAY: _encode_add_holiday,
    KIND_REMOVE_HOLIDAY: _encode_remove_holiday,

    KIND_WHIM_REFRESH: _encode_whim_refresh,
    KIND_WHIM_TOGGLE_LOCK: _encode_whim_toggle_lock,
    KIND_WHIMS_AWARD_PRIZE: _encode_whims_award_prize,
    KIND_REQUEST_SATISFACTION_REWARD_LIST: _encode_request_satisfaction_reward_list,

    KIND_REQUEST_PERKS_LIST: _encode_request_perks_list,
    KIND_UNLOCK_PERK: _encode_unlock_perk,
    KIND_UNLOCK_MULTIPLE_PERKS: _encode_unlock_multiple_perks,
    KIND_LOCK_ALL_PERKS: _encode_lock_all_perks,

    KIND_SHOW_RENTAL_UNIT_MANAGEMENT: _encode_show_rental_unit_management,
    KIND_NOTIFY_BUSINESS_RULES_STATE_CHANGE: _encode_notify_business_rules_state_change,
    KIND_SET_UNIT_RENT_PRICE: _encode_set_unit_rent_price,
    KIND_SET_UNIT_SIGNED_LEASE_LENGTH: _encode_set_unit_signed_lease_length,
    KIND_SELECT_TENANT: _encode_select_tenant,

    KIND_REQUEST_SHOW_DYNASTY_CONFIGURATOR: _encode_request_show_dynasty_configurator,
    KIND_CREATE_DYNASTY: _encode_create_dynasty,
    KIND_UPDATE_DYNASTY: _encode_update_dynasty,
    KIND_REMOVE_DYNASTY: _encode_remove_dynasty,

    KIND_SET_ALLOW_FAME: _encode_set_allow_fame,
    KIND_SELL_EXCESS_UTILITY: _encode_sell_excess_utility,
    KIND_SET_UTILITY_END_BILL_ACTION: _encode_set_utility_end_bill_action,

    KIND_SHOW_EXTEND_VACATION: _encode_show_extend_vacation,
    KIND_SHOW_LIGHT_EDITOR: _encode_show_light_editor,
    KIND_SET_COLOR_AND_INTENSITY: _encode_set_color_and_intensity,
    KIND_CHEAT: _encode_cheat,
    KIND_ORDER_FOR_TABLE: _encode_order_for_table,
    KIND_REFRESH_RESTAURANT_CONFIG: _encode_refresh_restaurant_config,

    KIND_SOCIAL_MEDIA_REMOVE_FRIEND: _encode_social_media_remove_friend,
    KIND_SOCIAL_MEDIA_ADD_REACTION: _encode_social_media_add_reaction,
    KIND_SOCIAL_MEDIA_MARK_POSTS_SEEN: _encode_social_media_mark_posts_seen,
    KIND_SOCIAL_MEDIA_MARK_MESSAGES_SEEN: _encode_social_media_mark_messages_seen,
    KIND_GENERATE_LIFESTYLES_DIALOG: _encode_generate_lifestyles_dialog,
    KIND_EQUIP_TRAIT: _encode_equip_trait,
    KIND_SHOW_LIFETIME_MILESTONES_PANEL: _encode_show_lifetime_milestones_panel,
    KIND_GENEALOGY_SHOW_FAMILY_TREE: _encode_genealogy_show_family_tree,

    KIND_UNIVERSITY_ENROLL: _encode_university_enroll,
    KIND_CANCEL_ENROLLMENT_DIALOG: _encode_cancel_enrollment_dialog,

    KIND_SHOW_HORSE_COMPETITION_UI: _encode_show_horse_competition_ui,
    KIND_PICK_NEW_HORSE_ASSIGNEE: _encode_pick_new_horse_assignee,
    KIND_START_HORSE_COMPETITION: _encode_start_horse_competition,
    KIND_GENERATE_SPELLBOOK_UI: _encode_generate_spellbook_ui,
    KIND_GET_CUSTOM_SCHEDULE: _encode_get_custom_schedule,
    KIND_GET_ULTIMATE_PROGRESS: _encode_get_ultimate_progress,
    KIND_GENERATE_NOTEBOOK: _encode_generate_notebook,
    KIND_SAVE_NOTES: _encode_save_notes,
    KIND_SET_PRIMARY_ASPIRATION_TRACK: _encode_set_primary_aspiration_track,
    KIND_SET_FAVORITE_CALENDAR_ENTRY: _encode_set_favorite_calendar_entry,
    KIND_UI_CREATE_HOVERTIP: _encode_ui_create_hovertip,

    KIND_GET_PHOTO_LIST: _encode_get_photo_list,
    KIND_FAMILY_TREE_SHOW: _encode_family_tree_show,
    KIND_STREET_CIVIC_REQUEST_ADD_PICKER: _encode_street_civic_request_add_picker,
    KIND_HANDLE_COMMUNITY_BOARD: _encode_handle_community_board,
    KIND_SHOW_COMMUNITY_BOARD: _encode_show_community_board,
    KIND_SOLVE_MOTIVE: _encode_solve_motive,
    KIND_OPEN_SIM_PROFILE_UI: _encode_open_sim_profile_ui,
    KIND_ZONE_MODIFIERS_UPDATE: _encode_zone_modifiers_update,

    KIND_CLEAR_PARENT_OBJECT: _encode_clear_parent_object,
    KIND_SET_BUILD_BUY_FLAGS: _encode_set_build_buy_flags,
    KIND_RESET_OBJECT: _encode_reset_object,
    KIND_SET_PARENT_OBJECT: _encode_set_parent_object,
    KIND_SET_DEFINITION: _encode_set_definition,
    KIND_SCALE_OBJECT: _encode_scale_object,
    KIND_BUILD_BUY_EXIT: _encode_build_buy_exit,
    KIND_SET_FLOOR_FEATURE: _encode_set_floor_feature,
    KIND_CREATE_SIM_INFO: _encode_create_sim_info,
}

_DECODERS = {
    KIND_GAME_NETWORK: _decode_game_network,
    KIND_GENERATE_CHOICES: _decode_generate_choices,
    KIND_GENERATE_PHONE_CHOICES: _decode_generate_phone_choices,
    KIND_SELECT_CHOICE: _decode_select_choice,
    KIND_PUSH_INTERACTION: _decode_push_interaction,
    KIND_CANCEL_INTERACTION: _decode_cancel_interaction,
    KIND_HAS_CHOICES: _decode_has_choices,
    KIND_HAS_CHOICES_RESPONSE: _decode_has_choices_response,
    KIND_SET_CLOCK_SPEED: _decode_set_clock_speed,
    KIND_SET_ACTIVE_SIM: _decode_set_active_sim,
    KIND_SET_AUTONOMY_ENABLED: _decode_set_autonomy_enabled,
    KIND_LIVE_DRAG_START: _decode_live_drag_start,
    KIND_LIVE_DRAG_START_RESPONSE: _decode_live_drag_start_response,
    KIND_LIVE_DRAG_END: _decode_live_drag_end,
    KIND_LIVE_DRAG_END_RESPONSE: _decode_live_drag_end_response,
    KIND_LIVE_DRAG_SELL: _decode_live_drag_sell,
    KIND_LIVE_DRAG_SELL_RESPONSE: _decode_live_drag_sell_response,

    KIND_CREATE_OBJECT: _decode_create_object,
    KIND_DESTROY_OBJECT: _decode_destroy_object,
    KIND_SET_OBJECT_LOCATION: _decode_set_object_location,

    KIND_DIALOG_RESPONSE: _decode_dialog_response,
    KIND_DIALOG_PICK_RESULT: _decode_dialog_pick_result,
    KIND_DIALOG_TEXT_INPUT: _decode_dialog_text_input,

    KIND_CREATE_SITUATION: _decode_create_situation,
    KIND_START_SITUATION_CREATION: _decode_start_situation_creation,
    KIND_START_SITUATION_CREATION_FOR_EDIT: _decode_start_situation_creation_for_edit,
    KIND_DESTROY_USER_FACING_SITUATION: _decode_destroy_user_facing_situation,
    KIND_SHOW_END_SITUATION_DIALOG: _decode_show_end_situation_dialog,

    KIND_MODIFY_HOUSEHOLD_FUNDS: _decode_modify_household_funds,
    KIND_INVENTORY_SELL_MULTIPLE: _decode_inventory_sell_multiple,
    KIND_PURCHASE_PICKER_RESPONSE: _decode_purchase_picker_response,
    KIND_INVENTORY_VIEW_UPDATE: _decode_inventory_view_update,

    KIND_TRAVEL_SIMS_TO_ZONE: _decode_travel_sims_to_zone,
    KIND_TRAVEL_FINISHED: _decode_travel_finished,
    KIND_END_VACATION: _decode_end_vacation,
    KIND_EXTEND_VACATION: _decode_extend_vacation,

    KIND_SEND_TO_WORK: _decode_send_to_work,
    KIND_LEAVE_WORK: _decode_leave_work,
    KIND_FIND_CAREER: _decode_find_career,
    KIND_SELECT_CAREER: _decode_select_career,
    KIND_STAY_LATE: _decode_stay_late,
    KIND_SET_FOLLOW_ENABLED: _decode_set_follow_enabled,
    KIND_CAREER_EVENT_SCORING_CLOSE: _decode_career_event_scoring_close,

    KIND_CREATE_CLUB: _decode_create_club,
    KIND_UPDATE_CLUB: _decode_update_club,
    KIND_REMOVE_CLUB: _decode_remove_club,
    KIND_ADD_SIM_TO_CLUB: _decode_add_sim_to_club,
    KIND_START_CLUB_GATHERING: _decode_start_club_gathering,
    KIND_END_CLUB_GATHERING: _decode_end_club_gathering,
    KIND_REQUEST_CLUB_INVITE: _decode_request_club_invite,

    KIND_SHOW_FESTIVAL_INFO: _decode_show_festival_info,
    KIND_SHOW_FESTIVAL_INFO_BY_UID: _decode_show_festival_info_by_uid,
    KIND_TRAVEL_TO_FESTIVAL_ZONE: _decode_travel_to_festival_zone,
    KIND_CANCEL_SCHEDULED_DRAMA_NODE: _decode_cancel_scheduled_drama_node,
    KIND_TRAVEL_TO_EVENT: _decode_travel_to_event,

    KIND_SET_BUSINESS_OPEN: _decode_set_business_open,
    KIND_SET_BUSINESS_MARKUP: _decode_set_business_markup,
    KIND_SET_BUSINESS_ADVERTISING: _decode_set_business_advertising,
    KIND_SET_BUSINESS_QUALITY: _decode_set_business_quality,
    KIND_TRANSFER_RETAIL_FUNDS: _decode_transfer_retail_funds,
    KIND_HIRE_BUSINESS_EMPLOYEE: _decode_hire_business_employee,
    KIND_FIRE_BUSINESS_EMPLOYEE: _decode_fire_business_employee,

    KIND_PUSH_REGISTER_BUSINESS: _decode_push_register_business,
    KIND_SHOW_SMALL_BUSINESS_CONFIGURATOR: _decode_show_small_business_configurator,
    KIND_REGISTER_SMALL_BUSINESS: _decode_register_small_business,
    KIND_UPDATE_SMALL_BUSINESS: _decode_update_small_business,
    KIND_SET_OPEN_SMALL_BUSINESS: _decode_set_open_small_business,
    KIND_SHOW_SMALL_BUSINESS_EMPLOYEE_MGMT: _decode_show_small_business_employee_mgmt,

    KIND_GET_HOLIDAY_DATA: _decode_get_holiday_data,
    KIND_GET_ACTIVE_HOLIDAY_DATA: _decode_get_active_holiday_data,
    KIND_UPDATE_HOLIDAY: _decode_update_holiday,
    KIND_ADD_HOLIDAY: _decode_add_holiday,
    KIND_REMOVE_HOLIDAY: _decode_remove_holiday,

    KIND_WHIM_REFRESH: _decode_whim_refresh,
    KIND_WHIM_TOGGLE_LOCK: _decode_whim_toggle_lock,
    KIND_WHIMS_AWARD_PRIZE: _decode_whims_award_prize,
    KIND_REQUEST_SATISFACTION_REWARD_LIST: _decode_request_satisfaction_reward_list,

    KIND_REQUEST_PERKS_LIST: _decode_request_perks_list,
    KIND_UNLOCK_PERK: _decode_unlock_perk,
    KIND_UNLOCK_MULTIPLE_PERKS: _decode_unlock_multiple_perks,
    KIND_LOCK_ALL_PERKS: _decode_lock_all_perks,

    KIND_SHOW_RENTAL_UNIT_MANAGEMENT: _decode_show_rental_unit_management,
    KIND_NOTIFY_BUSINESS_RULES_STATE_CHANGE: _decode_notify_business_rules_state_change,
    KIND_SET_UNIT_RENT_PRICE: _decode_set_unit_rent_price,
    KIND_SET_UNIT_SIGNED_LEASE_LENGTH: _decode_set_unit_signed_lease_length,
    KIND_SELECT_TENANT: _decode_select_tenant,

    KIND_REQUEST_SHOW_DYNASTY_CONFIGURATOR: _decode_request_show_dynasty_configurator,
    KIND_CREATE_DYNASTY: _decode_create_dynasty,
    KIND_UPDATE_DYNASTY: _decode_update_dynasty,
    KIND_REMOVE_DYNASTY: _decode_remove_dynasty,

    KIND_SET_ALLOW_FAME: _decode_set_allow_fame,
    KIND_SELL_EXCESS_UTILITY: _decode_sell_excess_utility,
    KIND_SET_UTILITY_END_BILL_ACTION: _decode_set_utility_end_bill_action,

    KIND_SHOW_EXTEND_VACATION: _decode_show_extend_vacation,
    KIND_SHOW_LIGHT_EDITOR: _decode_show_light_editor,
    KIND_SET_COLOR_AND_INTENSITY: _decode_set_color_and_intensity,
    KIND_CHEAT: _decode_cheat,
    KIND_ORDER_FOR_TABLE: _decode_order_for_table,
    KIND_REFRESH_RESTAURANT_CONFIG: _decode_refresh_restaurant_config,

    KIND_SOCIAL_MEDIA_REMOVE_FRIEND: _decode_social_media_remove_friend,
    KIND_SOCIAL_MEDIA_ADD_REACTION: _decode_social_media_add_reaction,
    KIND_SOCIAL_MEDIA_MARK_POSTS_SEEN: _decode_social_media_mark_posts_seen,
    KIND_SOCIAL_MEDIA_MARK_MESSAGES_SEEN: _decode_social_media_mark_messages_seen,
    KIND_GENERATE_LIFESTYLES_DIALOG: _decode_generate_lifestyles_dialog,
    KIND_EQUIP_TRAIT: _decode_equip_trait,
    KIND_SHOW_LIFETIME_MILESTONES_PANEL: _decode_show_lifetime_milestones_panel,
    KIND_GENEALOGY_SHOW_FAMILY_TREE: _decode_genealogy_show_family_tree,

    KIND_UNIVERSITY_ENROLL: _decode_university_enroll,
    KIND_CANCEL_ENROLLMENT_DIALOG: _decode_cancel_enrollment_dialog,

    KIND_SHOW_HORSE_COMPETITION_UI: _decode_show_horse_competition_ui,
    KIND_PICK_NEW_HORSE_ASSIGNEE: _decode_pick_new_horse_assignee,
    KIND_START_HORSE_COMPETITION: _decode_start_horse_competition,
    KIND_GENERATE_SPELLBOOK_UI: _decode_generate_spellbook_ui,
    KIND_GET_CUSTOM_SCHEDULE: _decode_get_custom_schedule,
    KIND_GET_ULTIMATE_PROGRESS: _decode_get_ultimate_progress,
    KIND_GENERATE_NOTEBOOK: _decode_generate_notebook,
    KIND_SAVE_NOTES: _decode_save_notes,
    KIND_SET_PRIMARY_ASPIRATION_TRACK: _decode_set_primary_aspiration_track,
    KIND_SET_FAVORITE_CALENDAR_ENTRY: _decode_set_favorite_calendar_entry,
    KIND_UI_CREATE_HOVERTIP: _decode_ui_create_hovertip,

    KIND_GET_PHOTO_LIST: _decode_get_photo_list,
    KIND_FAMILY_TREE_SHOW: _decode_family_tree_show,
    KIND_STREET_CIVIC_REQUEST_ADD_PICKER: _decode_street_civic_request_add_picker,
    KIND_HANDLE_COMMUNITY_BOARD: _decode_handle_community_board,
    KIND_SHOW_COMMUNITY_BOARD: _decode_show_community_board,
    KIND_SOLVE_MOTIVE: _decode_solve_motive,
    KIND_OPEN_SIM_PROFILE_UI: _decode_open_sim_profile_ui,
    KIND_ZONE_MODIFIERS_UPDATE: _decode_zone_modifiers_update,

    KIND_CLEAR_PARENT_OBJECT: _decode_clear_parent_object,
    KIND_SET_BUILD_BUY_FLAGS: _decode_set_build_buy_flags,
    KIND_RESET_OBJECT: _decode_reset_object,
    KIND_SET_PARENT_OBJECT: _decode_set_parent_object,
    KIND_SET_DEFINITION: _decode_set_definition,
    KIND_SCALE_OBJECT: _decode_scale_object,
    KIND_BUILD_BUY_EXIT: _decode_build_buy_exit,
    KIND_SET_FLOOR_FEATURE: _decode_set_floor_feature,
    KIND_CREATE_SIM_INFO: _decode_create_sim_info,
}


def encode_wrapper(wrapper):
    if not isinstance(wrapper, WrapperMessage):
        raise TypeError("wrapper must be WrapperMessage")
    if wrapper.kind is None:
        raise wire.WireError("wrapper.kind is required")
    field = _KIND_TO_FIELD.get(wrapper.kind)
    if field is None:
        raise wire.WireError("unknown wrapper kind %r" % wrapper.kind)
    encoder = _ENCODERS[wrapper.kind]
    nested = encoder(wrapper.body or {})
    return wire.encode_message([
        (1, "varint", wrapper.target_client),
        (2, "varint", wrapper.client_id),
        (field, "message", nested),
    ])


def decode_wrapper(raw):
    target_client = 0
    client_id = 0
    kind = None
    body = {}
    for number, wtype, value in wire.decode_fields(raw):
        if number == _F_TARGET_CLIENT and wtype == wire.WIRE_VARINT:
            target_client = wire.as_varint(value)
        elif number == _F_CLIENT_ID and wtype == wire.WIRE_VARINT:
            client_id = wire.as_varint(value)
        elif wtype == wire.WIRE_LEN and number in _FIELD_TO_KIND:
            kind = _FIELD_TO_KIND[number]
            body = _DECODERS[kind](value)
    return WrapperMessage(target_client=target_client, client_id=client_id, kind=kind, body=body)
