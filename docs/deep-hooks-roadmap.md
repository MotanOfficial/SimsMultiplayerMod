# Deep hooks roadmap

Host-authoritative Sims simulation. Joiners relay commands as Motanplayer
protobuf (`WrapperMessage`); the host fans native EA messages back via
`GameNetworkMessage` → `omega.send`.

Do **one phase at a time**. Each phase ends with: protobuf kinds + Override
hooks + MessageHandlers + unit tests. In-game smoke is noted but not blocking.

## Status

| Phase | Surface | Status |
|-------|---------|--------|
| P0 | Foundation (Override, DeepSession, DEEP_RELAY, Timeline, Client.send_message, generate/select/push) | DONE |
| P1 | Interaction surface complete: has_choices, cancel, phone pie | DONE |
| P2 | Clock authority (`GameClock` speed / pause barriers) | next |
| P3 | Active sim select + autonomy per player | DONE |
| P4 | Live drag | DONE |
| P5 | Object create / destroy / set location (build-buy core) | DONE |
| P6 | Dialogs | DONE |
| P7 | Situations | DONE |
| P8 | Inventory / funds hooks (deep path) | DONE |
| P9 | Travel / zone spin-up | DONE |
| P10 | Careers (send/leave/find/select/stay-late/follow) | DONE |
| P11 | Clubs (create/update/remove/member/gathering/invite) | DONE |
| P12 | Drama (festival info / travel / cancel scheduled) | DONE |
| P13 | Business (open/markup/ads/quality/funds/hire/fire) | DONE |
| P14 | Small business (register/update/open/configurator) | DONE |
| P15 | Holidays (get/add/update/remove) | DONE |
| P16 | Whims (refresh/lock/award/reward-list) | DONE |
| P17 | Bucks (perks list / unlock / lock) | DONE |
| P18 | Multi-unit (rental manage / rules / rent / lease / tenant) | DONE |
| P19 | Dynasty (show / create / update / remove) | DONE |
| P20 | Fame + bills (allow-fame / sell-excess / end-bill-action) | DONE |
| P21 | Travel groups show-extend (end/extend already in P9) | DONE |
| P22 | Lighting (show editor / set color+intensity) | DONE |
| P23 | Cheats (generic CheatMessage relay) | DONE |
| P24 | Restaurant (order-for-table / refresh-config) | DONE |
| P25 | Social media (remove-friend / reaction / mark-seen) | DONE |
| P26 | Traits (lifestyles dialog / equip) | DONE |
| P27 | Lifetime milestones panel | DONE |
| P28 | Genealogy show family tree | DONE |
| P29 | University (enroll / cancel-enrollment-dialog) | DONE |
| P30 | Horse competition (show / pick-assignee / start) | DONE |
| P31 | Spells (generate spellbook UI) | DONE |
| P32 | Custom schedules (get-schedule) | DONE |
| P33 | Ghost powers (ultimate progress) | DONE |
| P34 | Notebook (generate / save-notes) | DONE |
| P35 | Aspiration (set primary track) | DONE |
| P36 | Calendar (favorite entry) | DONE |
| P37 | Hovertip (ui create) | DONE |
| P38 | Photo get-list | DONE |
| P39 | Family-tree pack show | DONE |
| P40 | Civic policies (picker / board / show) | DONE |
| P41 | Statistics solve-motive | DONE |
| P42 | Relationship open sim-profile UI | DONE |
| P43 | Zone-modifier delta sync | DONE |
| P44 | Buy C-API extras (parent/flags/reset/definition/scale/exit/floor) | DONE |
| P45 | Zone spin-up batch spawn (joiner local) | DONE |
| P46 | Pregnancy create-sim-info fan-out | DONE |
| P47 | Adventure dialog route (host) + joiner suppress | DONE |
| P48 | Persistence save-using disconnect (joiner) | DONE |
| — | Deep NetworkedCommand-style surface sweep complete | DONE |

## Phase rules

1. Study the open-source **concept** (which game method, which message).
2. Implement Motanplayer-owned code under `simmp_client/deep/` + `simmp/deep/`.
3. Never paste decompiled proprietary sources.
4. Keep Python 3.7-safe, no `asyncio`/`uuid`/`ssl` in game-shipped modules.
5. Offline unit tests for encode/decode + Override role install.
6. Host path must tolerate missing game APIs (try/except, no crash).

## P1 done criteria

- [x] Roadmap written
- [x] Joiner overrides: `has_choices`, `cancel_si`/`cancel_super_interaction`, `generate_phone_choices`
- [x] Host handlers rebuild Interactable / cancel / phone ChoiceMenu
- [ ] `has_choices_response` carries opaque Interactable bytes → joiner Distributor event
- [x] Tests for new protobuf kinds

## Config

`deep_hooks` / `want_host` in `Sims4Multiplayer.json` (defaults on).


## P2 done criteria

- [x] KIND_SET_CLOCK_SPEED protobuf (set / push / pop)
- [x] Joiner Overrides on GameClock.set_clock_speed / push_speed / pop_speed
- [x] Host MessageHandler applies via game_clock_service
- [x] Unit test roundtrip


## P3 done criteria

- [x] KIND_SET_ACTIVE_SIM + joiner/host Client active-sim Overrides
- [x] Host ctive_sims map (player_id -> sim_id)
- [x] KIND_SET_AUTONOMY_ENABLED + host LIMITED_ONLY / UNDEFINED apply
- [x] Unit test roundtrips


## P4 done criteria

- [x] Six live-drag protobuf kinds (start/end/sell + responses)
- [x] Joiner Overrides: live_drag.start, live_drag.end, c_api_live_drag_end, Client.sell_live_drag_object
- [x] Host handlers start/end/sell on real objects; joiner applies Distributor LiveDrag ops
- [x] Transform packed as floats (no jsonpickle)
- [x] Unit test roundtrips


## P5 done criteria

- [x] `KIND_CREATE_OBJECT` / `KIND_DESTROY_OBJECT` / `KIND_SET_OBJECT_LOCATION`
- [x] Overrides on `system.c_api_create_object`, `c_api_destroy_object`, `build_buy.c_api_set_object_location_ex` (ALL roles, shared IDs)
- [x] Peer handlers apply create/destroy/set_parent; transform as floats
- [x] Unit test roundtrips

## P6 done criteria

- [x] KIND_DIALOG_RESPONSE / KIND_DIALOG_PICK_RESULT / KIND_DIALOG_TEXT_INPUT
- [x] Joiner Overrides on ui_dialog_respond / ui_dialog_pick_result / ui_dialog_text_input
- [x] Host tracks ctive_dialogs via UiDialogService.dialog_show; handlers apply respond/pick/text
- [x] Host closes joiner dialog UI via MSG_UI_DIALOG_CLOSE GameNetworkMessage
- [x] Unit test roundtrips

## P7 done criteria

- [x] Five situation protobuf kinds (create / start / start-for-edit / destroy / show-end-dialog)
- [x] Joiner Overrides on matching `situation_commands` entry points
- [x] Host handlers: guest-list create, SituationPrepare fan-out, destroy user-facing, end-dialog via host command + P6 dialogs
- [x] Unit test roundtrips

## P8 done criteria

- [x] KIND_MODIFY_HOUSEHOLD_FUNDS + joiner Override on `build_buy.c_api_modify_household_funds`
- [x] Inventory sell / purchase-picker / view-update protobuf relays
- [x] Host handlers apply funds + inventory mutations; purchase replays original command
- [x] Unit test roundtrips

## P9 done criteria

- [x] Joiner `SimSpawnerService.batch_spawn_during_zone_spin_up` Override
- [x] `KIND_TRAVEL_FINISHED` loading-screen handshake + host clock unpause
- [x] `KIND_TRAVEL_SIMS_TO_ZONE` joiner relay; soft-block travel map UI on joiners
- [x] `KIND_END_VACATION` / `KIND_EXTEND_VACATION` travel-group relays
- [x] Unit test roundtrips

## P10 done criteria

- [x] Seven career protobuf kinds (send/leave/find/select/stay-late/follow/scoring-close)
- [x] Joiner Overrides on matching `career_commands` entry points
- [x] Host handlers mutate career tracker / push find-job / extend session / post-event travel
- [x] Unit test roundtrips

## P11 done criteria

- [x] Seven club protobuf kinds (create/update/remove/add-sim/start/end gathering/invite)
- [x] Joiner Overrides on matching `club_commands` entry points
- [x] Host handlers merge opaque Club text-format data + ClubService mutations
- [x] Unit test roundtrips

## P12 done criteria

- [x] Five drama protobuf kinds (show festival info / by-uid / travel zone / cancel / travel event)
- [x] Joiner Overrides on matching `drama_commands` entry points
- [x] Host handlers run festival UI commands + cancel scheduled nodes + push travel affordances
- [x] Unit test roundtrips

## P13 done criteria

- [x] Seven business protobuf kinds (open/markup/advertising/quality/transfer/hire/fire)
- [x] Joiner Overrides on `business_commands` + `retail_commands.transfer_*`
- [x] Host handlers mutate BusinessManager / transfer funds / push hire-fire affordances
- [x] Unit test roundtrips

## P14 done criteria

- [x] Six small-business protobuf kinds (push-register/configurator/register/update/open/employee-mgmt)
- [x] Joiner Overrides on matching `business_commands` small-business entry points
- [x] Host handlers make_owner / update_from_ui / set_open / push register affordance
- [x] Unit test roundtrips

## P15 done criteria

- [x] Five holiday protobuf kinds (get / get-active / update / add / remove)
- [x] Joiner Overrides on `holiday_commands`
- [x] Host handlers mutate `holiday_service`; get-* replays original for UI fan-out
- [x] Unit test roundtrips

## P16 done criteria

- [x] Four whim protobuf kinds (refresh / toggle-lock / award-prize / request-reward-list)
- [x] Joiner Overrides on `whim_commands` + `sim_commands` satisfaction entry points
- [x] Host handlers mutate whim_tracker / satisfaction_tracker; reward list fans via Distributor
- [x] Unit test roundtrips

## P17 done criteria

- [x] Four bucks protobuf kinds (request-perks-list / unlock / unlock-multiple / lock-all)
- [x] Joiner Overrides on `bucks_commands` entry points
- [x] Host handlers mutate bucks_tracker; request-list replays original for UI fan-out
- [x] Unit test roundtrips

## P18 done criteria

- [x] Five multi-unit protobuf kinds (show-management / notify-rules / rent / lease / select-tenant)
- [x] Joiner Overrides on `multi_unit_commands` + `areaserver` rules notify
- [x] Host handlers mutate rental business_manager / tenant_application_service; show replays original
- [x] Unit test roundtrips

## P19 done criteria

- [x] Four dynasty protobuf kinds (show-configurator / create / update / remove)
- [x] Joiner Overrides on `dynasty_commands` entry points
- [x] Host handlers mutate `dynasty_service`; show replays original for UI fan-out
- [x] Unit test roundtrips

## P20 done criteria

- [x] Three protobuf kinds (set-allow-fame / sell-excess-utility / set-utility-end-bill-action)
- [x] Joiner Overrides on `fame_commands` + `bills_commands`
- [x] Host handlers apply force_allow_fame / bills_manager mutations
- [x] Unit test roundtrips

## P21 done criteria

- [x] KIND_SHOW_EXTEND_VACATION (end/extend already in P9 travel)
- [x] Joiner Override + host show-extend dialog path
- [x] Unit test roundtrips

## P22 done criteria

- [x] Two lighting protobuf kinds
- [x] Joiner Overrides on `lighting_commands`
- [x] Host handlers replay show editor + update color dialog
- [x] Unit test roundtrips

## P23 done criteria

- [x] Generic KIND_CHEAT protobuf
- [x] Joiner Overrides on money / testing / motives / skills / careers cheats
- [x] Host dispatcher by cheat_name
- [x] Unit test roundtrips

## P24 done criteria

- [x] Two restaurant protobuf kinds (order / refresh-config)
- [x] Joiner Overrides on `restaurant_commands`
- [x] Host handlers mutate restaurant zone director
- [x] Unit test roundtrips

## P25 done criteria

- [x] Four social-media protobuf kinds
- [x] Joiner Overrides on `social_media_commands`
- [x] Host handlers mutate social_media_service / replay reactions
- [x] Unit test roundtrips

## P26 done criteria

- [x] Two trait protobuf kinds (lifestyles dialog / equip)
- [x] Joiner Overrides on `trait_commands`
- [x] Host handlers show lifestyles dialog + add_trait
- [x] Unit test roundtrips

## P27 done criteria

- [x] KIND_SHOW_LIFETIME_MILESTONES_PANEL
- [x] Joiner Override + host replay
- [x] Unit test roundtrip

## P28 done criteria

- [x] KIND_GENEALOGY_SHOW_FAMILY_TREE
- [x] Joiner Override + host replay of genealogy command
- [x] Unit test roundtrip

## P29 done criteria

- [x] Two university protobuf kinds (enroll / cancel-enrollment-dialog)
- [x] Joiner Overrides on `university_commands`
- [x] Host handlers mutate degree_tracker + tuition/loan; cancel dialog callback
- [x] Unit test roundtrips

## P30 done criteria

- [x] Three horse protobuf kinds
- [x] Joiner Overrides on horse_competition_commands
- [x] Host handlers show UI / pick assignee / start competition
- [x] Unit test roundtrips

## P31 done criteria

- [x] KIND_GENERATE_SPELLBOOK_UI
- [x] Joiner Override + host replay
- [x] Unit test roundtrip

## P32 done criteria

- [x] KIND_GET_CUSTOM_SCHEDULE
- [x] Joiner Override + host replay
- [x] Unit test roundtrip

## P33 done criteria

- [x] KIND_GET_ULTIMATE_PROGRESS
- [x] Joiner Override + host replay
- [x] Unit test roundtrip

## P34 done criteria

- [x] Two notebook protobuf kinds
- [x] Joiner Overrides + host replay
- [x] Unit test roundtrips

## P35 done criteria

- [x] KIND_SET_PRIMARY_ASPIRATION_TRACK
- [x] Host sets primary_aspiration
- [x] Unit test roundtrip

## P36 done criteria

- [x] KIND_SET_FAVORITE_CALENDAR_ENTRY
- [x] Host calendar_service favorite
- [x] Unit test roundtrip

## P37 done criteria

- [x] KIND_UI_CREATE_HOVERTIP
- [x] Host on_hovertip_requested + Distributor op
- [x] Unit test roundtrip

## P38 done criteria

- [x] KIND_GET_PHOTO_LIST
- [x] Joiner Override on photo_commands.get_photo_list
- [x] Host replays get_photo_list
- [x] Unit test roundtrip

## P39 done criteria

- [x] KIND_FAMILY_TREE_SHOW
- [x] Joiner Override on family_tree_show_family_tree
- [x] Host replay
- [x] Unit test roundtrip

## P40 done criteria

- [x] Three civic protobuf kinds
- [x] Joiner Overrides on street civic commands
- [x] Host handlers
- [x] Unit test roundtrips

## P41 done criteria

- [x] KIND_SOLVE_MOTIVE
- [x] Joiner Override + host replay
- [x] Unit test roundtrip

## P42 done criteria

- [x] KIND_OPEN_SIM_PROFILE_UI
- [x] Joiner Override + host replay
- [x] Unit test roundtrip

## P43 done criteria

- [x] KIND_ZONE_MODIFIERS_UPDATE
- [x] Joiner Override on PersistenceService unlock
- [x] Host applies lot_traits delta
- [x] Unit test roundtrip

## P44 done criteria

- [x] Eight buy protobuf kinds
- [x] Joiner Overrides on C-API parent/flags/reset/definition/scale + exit callback
- [x] Host handlers + joiner floor-feature apply
- [x] Unit test roundtrips

## P45 done criteria

- [x] Joiner Override on SimSpawnerService.batch_spawn_during_zone_spin_up
- [x] Forces BATCH_SPAWNING drain locally

## P46 done criteria

- [x] KIND_CREATE_SIM_INFO opaque bytes
- [x] Host Override fans SimData; joiner loads selectable SimInfo
- [x] Unit test roundtrip

## P47 done criteria

- [x] Host Override on AdventureMoment.run_adventure sets waiting_for_callback_player_id
- [x] Joiner Override suppresses local adventure resolution
- [x] Unit test with mocked AdventureMoment

## P48 done criteria

- [x] Joiner Override on PersistenceService.save_using
- [x] Disconnects multiplayer when allow_shutdown (via registered callback)
- [x] connectivity.bind registers disconnect callback
- [x] Unit test with mocked PersistenceService

