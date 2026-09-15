import unittest

from simmp_client.state.world import WorldMirror, lerp


class LerpTests(unittest.TestCase):
    def test_lerp_bounds(self):
        self.assertEqual(lerp(0, 10, 0.0), 0.0)
        self.assertEqual(lerp(0, 10, 1.0), 10.0)
        self.assertEqual(lerp(0, 10, 0.5), 5.0)


class WorldMirrorTests(unittest.TestCase):
    def test_apply_full_replaces_catalog(self):
        mirror = WorldMirror()
        mirror.apply_full(
            "lobby",
            [
                {"key": "sofa", "owner": 1000, "fields": {"x": 1.0, "y": 2.0, "z": 3.0}},
                {"key": "table", "owner": None, "fields": {}},
            ],
        )
        self.assertEqual(mirror.room_id, "lobby")
        self.assertEqual(mirror.count(), 2)
        self.assertEqual(mirror.get("sofa").owner, 1000)
        self.assertEqual(mirror.get("table").owner, None)

    def test_apply_delta_merges_fields(self):
        mirror = WorldMirror()
        mirror.apply_full("lobby", [{"key": "sofa", "owner": 1000, "fields": {"x": 1.0}}])
        mirror.apply_delta("lobby", 1, [{"key": "sofa", "fields": {"y": 5.0, "z": 0.0}}])
        self.assertEqual(mirror.last_seq, 1)
        self.assertEqual(mirror.get("sofa").fields, {"x": 1.0, "y": 5.0, "z": 0.0})

    def test_apply_delta_stale_seq_ignored(self):
        mirror = WorldMirror()
        mirror.apply_full("lobby", [{"key": "sofa", "owner": 1000, "fields": {"x": 1.0}}])
        mirror.apply_delta("lobby", 5, [{"key": "sofa", "fields": {"y": 1.0}}])
        mirror.apply_delta("lobby", 4, [{"key": "sofa", "fields": {"y": 99.0}}])
        self.assertEqual(mirror.last_seq, 5)
        self.assertEqual(mirror.get("sofa").fields["y"], 1.0)

    def test_apply_delta_wrong_room_ignored(self):
        mirror = WorldMirror()
        mirror.apply_full("lobby", [{"key": "sofa", "owner": None, "fields": {}}])
        mirror.apply_delta("alpha", 1, [{"key": "sofa", "fields": {"x": 1.0}}])
        self.assertNotEqual(mirror.get("sofa").fields.get("x"), 1.0)

    def test_apply_delta_creates_unknown_key(self):
        mirror = WorldMirror()
        mirror.apply_full("lobby", [])
        mirror.apply_delta("lobby", 1, [{"key": "sofa", "fields": {"x": 2.0}}])
        self.assertIn("sofa", mirror.objects)

    def test_apply_ownership_updates_owner(self):
        mirror = WorldMirror()
        mirror.apply_full("lobby", [{"key": "sofa", "owner": None, "fields": {}}])
        mirror.apply_ownership("sofa", 1000)
        self.assertEqual(mirror.get("sofa").owner, 1000)
        mirror.apply_claim_ack("sofa", None)
        self.assertIsNone(mirror.get("sofa").owner)

    def test_position_and_display_position_smoothing(self):
        mirror = WorldMirror()
        mirror.apply_full("lobby", [{"key": "sofa", "owner": None, "fields": {"x": 0.0, "y": 0.0, "z": 0.0}}])
        sofa = mirror.get("sofa")
        # No anchor yet -> exact.
        self.assertEqual(mirror.get("sofa").display_position(now=100.0), (0.0, 0.0, 0.0))

        # A move anchors the old position and eases toward the target.
        sofa.merge_fields({"x": 10.0, "y": 0.0, "z": 0.0}, now=100.0)
        self.assertEqual(sofa.display_position(now=100.0), (0.0, 0.0, 0.0))
        self.assertEqual(sofa.display_position(now=100.25, rate=2.0), (5.0, 0.0, 0.0))
        self.assertEqual(sofa.display_position(now=101.0, rate=2.0), (10.0, 0.0, 0.0))

    def test_position_missing_fields_returns_none(self):
        mirror = WorldMirror()
        mirror.apply_full("lobby", [{"key": "table", "owner": None, "fields": {"state": "clean"}}])
        self.assertIsNone(mirror.get("table").position())