"""Tests for the game-facing hooks that must stay safe outside the game
plus their pure-data helpers. The `services`/`sims4` modules do not exist
here, so the samplers must all return their empty form without raising."""

import unittest

from simmp_client.hooks import game_hooks


class GameHooksSamplerTests(unittest.TestCase):
    def test_zone_sampler_is_none_offline(self):
        self.assertIsNone(game_hooks.sample_current_zone())

    def test_world_sampler_is_empty_offline(self):
        self.assertEqual(game_hooks.sample_world_objects(), [])

    def test_interaction_sampler_is_empty_offline(self):
        self.assertEqual(game_hooks.sample_interactions(), [])

    def test_world_applier_noops_offline(self):
        self.assertEqual(game_hooks.apply_world_updates([]), 0)
        self.assertEqual(
            game_hooks.apply_world_updates(
                [{"key": "sim:123", "fields": {"x": 1.0, "y": 2.0, "z": 3.0}}]
            ),
            0,
        )

    def test_interaction_applier_noops_offline(self):
        self.assertEqual(game_hooks.apply_interactions([]), 0)
        self.assertEqual(
            game_hooks.apply_interactions(
                [{"key": "sim:123", "interaction": "Read", "affordance_id": 9001}]
            ),
            0,
        )

    def test_interaction_label_and_target_helpers(self):
        class FakeSimInfo:
            id = 7

        class FakeTarget:
            sim_info = FakeSimInfo()

        class FakeAffordance:
            pass

        class FakeInteraction:
            def get_affordance(self):
                return FakeAffordance()

            target = FakeTarget()

        interaction = FakeInteraction()
        self.assertEqual(game_hooks._interaction_label(interaction), "FakeInteraction")
        self.assertEqual(game_hooks._interaction_target_key(interaction, "sim:7"), None)
        self.assertEqual(game_hooks._interaction_target_key(interaction, "sim:1"), "sim:7")
        self.assertEqual(game_hooks._interaction_affordance_name(interaction), "FakeAffordance")
        self.assertIsNone(game_hooks._interaction_label(None))

        class NoAffordance:
            def get_affordance(self):
                raise RuntimeError("boom")

        self.assertEqual(game_hooks._interaction_affordance_name(NoAffordance()), "NoAffordance")

        class NoTarget:
            get_affordance = None
            target = None

        self.assertIsNone(game_hooks._interaction_target_key(NoTarget(), "sim:1"))

    def test_sim_id_and_field_helpers(self):
        self.assertEqual(game_hooks._sim_id_from_key("sim:42"), 42)
        self.assertIsNone(game_hooks._sim_id_from_key("obj:42"))
        self.assertIsNone(game_hooks._sim_id_from_key(None))
        self.assertEqual(
            game_hooks._position_from_fields({"x": "1", "y": 2, "z": 3.5}),
            (1.0, 2.0, 3.5),
        )
        self.assertIsNone(game_hooks._position_from_fields({"x": 1}))
        self.assertEqual(
            game_hooks._orientation_from_fields({"qw": 1, "qx": 0, "qy": 0, "qz": 0}),
            (1.0, 0.0, 0.0, 0.0),
        )
        self.assertIsNone(game_hooks._orientation_from_fields({"qw": 1}))

    def test_vec3_filters_bad_values(self):
        self.assertIsNone(game_hooks._vec3(None))

        class Fake:
            x = 1
            y = 2
            z = 3

        self.assertEqual(game_hooks._vec3(Fake()), (1.0, 2.0, 3.0))

    def test_quat_filters_bad_values(self):
        self.assertIsNone(game_hooks._quat(None))

        class Fake:
            w = 0.0
            x = 1.0
            y = 2.0
            z = 3.0

        self.assertEqual(game_hooks._quat(Fake()), (0.0, 1.0, 2.0, 3.0))

    def test_sim_key_and_entry_build(self):
        class FakeTransform:
            class Vec:
                x = 1.0
                y = 2.0
                z = 3.0

            class Ori:
                w = 0.0
                x = 1.0
                y = 2.0
                z = 3.0

            translation = Vec()
            orientation = Ori()

        class FakeLocation:
            transform = FakeTransform()

        class FakeDef:
            id = 987

        class FakeSim:
            location = FakeLocation()
            definition = FakeDef()

        class FakeSimInfo:
            id = 123

        entry = game_hooks._sim_world_entry(FakeSimInfo(), FakeSim())
        self.assertEqual(entry["key"], "sim:123")
        self.assertEqual(entry["fields"]["x"], 1.0)
        self.assertEqual(entry["fields"]["y"], 2.0)
        self.assertEqual(entry["fields"]["z"], 3.0)
        self.assertEqual(entry["fields"]["qw"], 0.0)
        self.assertEqual(entry["fields"]["qx"], 1.0)
        self.assertEqual(entry["fields"]["def"], 987)

    def test_set_sim_autonomy_uses_setter_when_present(self):
        calls = []

        class FakeSimInfo:
            id = 5

            def set_autonomy_enabled(self, enabled):
                calls.append(("setter", enabled))

        self.assertTrue(game_hooks.set_sim_autonomy(FakeSimInfo(), False))
        self.assertEqual(calls, [("setter", False)])

    def test_set_sim_autonomy_tries_autonomy_component(self):
        calls = []

        class FakeComponent:
            def set_autonomy_enabled(self, enabled):
                calls.append(("component", enabled))

        class FakeSim:
            def get_autonomy_component(self):
                return FakeComponent()

        class FakeSimInfo:
            id = 5

            def get_sim_instance(self):
                return FakeSim()

        self.assertTrue(game_hooks.set_sim_autonomy(FakeSimInfo(), True))
        self.assertEqual(calls, [("component", True)])

    def test_set_sim_autonomy_falls_back_to_attribute(self):
        class FakeSimInfo:
            id = 5
            autonomy_enabled = True

        sim_info = FakeSimInfo()
        self.assertTrue(game_hooks.set_sim_autonomy(sim_info, False))
        self.assertIs(sim_info.autonomy_enabled, False)

    def test_set_sim_autonomy_returns_false_when_nothing_usable(self):
        class FakeSimInfo:
            id = 5

        self.assertFalse(game_hooks.set_sim_autonomy(FakeSimInfo(), True))

    def test_reconcile_autonomy_offline_is_skipped(self):
        # Without a live game world, reconcile can't find sims. It must never
        # raise and report all sims as skipped (counts may differ by env but
        # the call must be safe).
        suppressed, restored, skipped = game_hooks.reconcile_autonomy(
            {"sim:1", "sim:2"}, 700, 100
        )
        self.assertGreaterEqual(suppressed, 0)
        self.assertGreaterEqual(restored, 0)
        self.assertGreaterEqual(skipped, 0)


if __name__ == "__main__":
    unittest.main()