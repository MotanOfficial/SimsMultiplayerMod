"""Deep host-authoritative hooks + protobuf command relays."""

from simmp_client.deep.session import SESSION  # noqa: F401
from simmp_client.deep.override import Override, Role  # noqa: F401
from simmp_client.deep.message_handler import MessageHandler  # noqa: F401


def install():
    """Register game patches that activate when DeepSession.activate() runs."""
    from simmp_client.deep import game_network
    from simmp_client.deep import timeline
    from simmp_client.deep import interactions
    from simmp_client.deep import clock as deep_clock
    from simmp_client.deep import sim_select
    from simmp_client.deep import autonomy as deep_autonomy
    from simmp_client.deep import live_drag
    from simmp_client.deep import objects as deep_objects
    from simmp_client.deep import dialogs as deep_dialogs
    from simmp_client.deep import situations as deep_situations
    from simmp_client.deep import inventory as deep_inventory
    from simmp_client.deep import travel as deep_travel
    from simmp_client.deep import careers as deep_careers
    from simmp_client.deep import clubs as deep_clubs
    from simmp_client.deep import drama as deep_drama
    from simmp_client.deep import business as deep_business
    from simmp_client.deep import small_business as deep_small_business
    from simmp_client.deep import holidays as deep_holidays
    from simmp_client.deep import whims as deep_whims
    from simmp_client.deep import bucks as deep_bucks
    from simmp_client.deep import multi_unit as deep_multi_unit
    from simmp_client.deep import dynasty as deep_dynasty
    from simmp_client.deep import fame as deep_fame
    from simmp_client.deep import bills as deep_bills
    from simmp_client.deep import travel_groups as deep_travel_groups
    from simmp_client.deep import lighting as deep_lighting
    from simmp_client.deep import cheats as deep_cheats
    from simmp_client.deep import restaurant as deep_restaurant
    from simmp_client.deep import social_media as deep_social_media
    from simmp_client.deep import traits as deep_traits
    from simmp_client.deep import milestones as deep_milestones
    from simmp_client.deep import genealogy as deep_genealogy
    from simmp_client.deep import university as deep_university
    from simmp_client.deep import horse_competition as deep_horse
    from simmp_client.deep import spells as deep_spells
    from simmp_client.deep import custom_schedules as deep_schedules
    from simmp_client.deep import ghost_powers as deep_ghost
    from simmp_client.deep import notebook as deep_notebook
    from simmp_client.deep import aspiration as deep_aspiration
    from simmp_client.deep import calendar as deep_calendar
    from simmp_client.deep import hovertip as deep_hovertip
    from simmp_client.deep import photo as deep_photo
    from simmp_client.deep import family_tree as deep_family_tree
    from simmp_client.deep import civic_policies as deep_civic
    from simmp_client.deep import statistics as deep_statistics
    from simmp_client.deep import relationship as deep_relationship
    from simmp_client.deep import zone_modifier as deep_zone_modifier
    from simmp_client.deep import buy as deep_buy
    from simmp_client.deep import zone_spin_up as deep_zone_spin_up
    from simmp_client.deep import pregnancy as deep_pregnancy
    from simmp_client.deep import adventure as deep_adventure
    from simmp_client.deep import persistence as deep_persistence

    ok = True
    ok = game_network.install_client_send_message_hooks() and ok
    ok = timeline.install_timeline_hooks() and ok
    ok = interactions.install_interaction_command_hooks() and ok
    ok = deep_clock.install_clock_hooks() and ok
    ok = sim_select.install_sim_select_hooks() and ok
    ok = deep_autonomy.install_autonomy_hooks() and ok
    ok = live_drag.install_live_drag_hooks() and ok
    ok = deep_objects.install_object_hooks() and ok
    ok = deep_dialogs.install_dialog_hooks() and ok
    ok = deep_situations.install_situation_hooks() and ok
    ok = deep_inventory.install_inventory_hooks() and ok
    ok = deep_travel.install_travel_hooks() and ok
    ok = deep_careers.install_career_hooks() and ok
    ok = deep_clubs.install_club_hooks() and ok
    ok = deep_drama.install_drama_hooks() and ok
    ok = deep_business.install_business_hooks() and ok
    ok = deep_small_business.install_small_business_hooks() and ok
    ok = deep_holidays.install_holiday_hooks() and ok
    ok = deep_whims.install_whim_hooks() and ok
    ok = deep_bucks.install_bucks_hooks() and ok
    ok = deep_multi_unit.install_multi_unit_hooks() and ok
    ok = deep_dynasty.install_dynasty_hooks() and ok
    ok = deep_fame.install_fame_hooks() and ok
    ok = deep_bills.install_bills_hooks() and ok
    ok = deep_travel_groups.install_travel_group_hooks() and ok
    ok = deep_lighting.install_lighting_hooks() and ok
    ok = deep_cheats.install_cheat_hooks() and ok
    ok = deep_restaurant.install_restaurant_hooks() and ok
    ok = deep_social_media.install_social_media_hooks() and ok
    ok = deep_traits.install_trait_hooks() and ok
    ok = deep_milestones.install_milestone_hooks() and ok
    ok = deep_genealogy.install_genealogy_hooks() and ok
    ok = deep_university.install_university_hooks() and ok
    ok = deep_horse.install_horse_competition_hooks() and ok
    ok = deep_spells.install_spell_hooks() and ok
    ok = deep_schedules.install_custom_schedule_hooks() and ok
    ok = deep_ghost.install_ghost_powers_hooks() and ok
    ok = deep_notebook.install_notebook_hooks() and ok
    ok = deep_aspiration.install_aspiration_hooks() and ok
    ok = deep_calendar.install_calendar_hooks() and ok
    ok = deep_hovertip.install_hovertip_hooks() and ok
    ok = deep_photo.install_photo_hooks() and ok
    ok = deep_family_tree.install_family_tree_hooks() and ok
    ok = deep_civic.install_civic_policy_hooks() and ok
    ok = deep_statistics.install_statistics_hooks() and ok
    ok = deep_relationship.install_relationship_hooks() and ok
    ok = deep_zone_modifier.install_zone_modifier_hooks() and ok
    ok = deep_buy.install_buy_hooks() and ok
    ok = deep_zone_spin_up.install_zone_spin_up_hooks() and ok
    ok = deep_pregnancy.install_pregnancy_hooks() and ok
    ok = deep_adventure.install_adventure_hooks() and ok
    ok = deep_persistence.install_persistence_hooks() and ok
    return ok
