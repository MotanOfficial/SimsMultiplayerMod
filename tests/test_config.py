import json
import os
import tempfile
import unittest
from unittest import mock

from simmp_client import config as cfg


class ClientIdTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._config = os.path.join(self._tmp.name, "Sims4Multiplayer.json")

    def tearDown(self):
        self._tmp.cleanup()

    def _sidecar(self):
        return os.path.join(self._tmp.name, "Sims4Multiplayer.client_id")

    def test_client_id_is_created_valid_and_stable(self):
        with open(self._config, "w", encoding="utf-8") as handle:
            handle.write("{}")
        first = cfg.load_or_create_client_id(explicit_config_path=self._config)
        self.assertRegex(first, r"^[0-9a-f]{32}$")
        self.assertTrue(os.path.isfile(self._sidecar()))
        second = cfg.load_or_create_client_id(explicit_config_path=self._config)
        self.assertEqual(first, second, "the id must be reloaded, not regenerated")

    def test_client_id_regenerated_when_stored_value_is_garbage(self):
        with open(self._config, "w", encoding="utf-8") as handle:
            handle.write("{}")
        with open(self._sidecar(), "w", encoding="utf-8") as handle:
            handle.write("not-an-id")
        client_id = cfg.load_or_create_client_id(explicit_config_path=self._config)
        self.assertRegex(client_id, r"^[0-9a-f]{32}$")
        self.assertNotEqual(client_id, "not-an-id")

    def test_client_id_works_without_a_config_file(self):
        # No config anywhere: the sidecar falls back to the Mods folder
        # inferred from USERPROFILE, which the test redirects to the tmp dir.
        fake_profile = self._tmp.name
        expected_dir = os.path.join(
            fake_profile, "Documents", "Electronic Arts", "The Sims 4", "Mods"
        )
        with mock.patch.dict(
            os.environ, {"USERPROFILE": fake_profile, "SIM4_MP_CONFIG": ""}
        ):
            client_id = cfg.load_or_create_client_id()
        self.assertRegex(client_id, r"^[0-9a-f]{32}$")
        self.assertTrue(os.path.isfile(os.path.join(expected_dir, "Sims4Multiplayer.client_id")))

    def test_client_id_never_raises_on_unwritable_path(self):
        # A config inside a read-only location must still yield a usable id.
        config = os.path.join(self._tmp.name, "ro", "Sims4Multiplayer.json")
        os.makedirs(os.path.dirname(config))
        with open(config, "w", encoding="utf-8") as handle:
            handle.write("{}")
        os.chmod(os.path.dirname(config), 0o500)  # read-only directory
        try:
            client_id = cfg.load_or_create_client_id(explicit_config_path=config)
        finally:
            os.chmod(os.path.dirname(config), 0o700)
        self.assertRegex(client_id, r"^[0-9a-f]{32}$")


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._path = os.path.join(self._tmp.name, "Sims4Multiplayer.json")

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, data):
        with open(self._path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)

    def test_default_config_returns_copy(self):
        first = cfg.default_config()
        second = cfg.default_config()
        self.assertEqual(first, second)
        first["host"] = "changed"
        self.assertNotEqual(first, cfg.default_config())

    def test_load_uses_defaults_when_keys_missing(self):
        self._write({"host": "myhost"})
        loaded = cfg.load_config(self._path)
        self.assertEqual(loaded["host"], "myhost")
        self.assertEqual(loaded["port"], 8765)
        self.assertEqual(loaded["auto_connect"], False)
        self.assertEqual(loaded["presence_interval"], 5.0)
        self.assertEqual(loaded["presence_ttl"], 30.0)
        self.assertEqual(loaded["auto_accept_travel"], True)
        self.assertEqual(loaded["world_sync"], False)
        self.assertEqual(loaded["deep_hooks"], True)
        self.assertEqual(loaded["world_interval"], 5.0)
        self.assertEqual(loaded["interaction_sync"], True)
        self.assertEqual(loaded["sync_funds"], False)
        self.assertEqual(loaded["build_sync"], False)
        self.assertEqual(loaded["want_host"], True)
        self.assertEqual(loaded["interaction_interval"], 5.0)
        self.assertEqual(loaded["ui_dialogs"], True)
        self.assertEqual(loaded["auto_reconnect"], True)
        self.assertEqual(loaded["reconnect_backoff_min"], 2.0)
        self.assertEqual(loaded["reconnect_backoff_max"], 30.0)
        self.assertEqual(loaded["min_players"], 2)

    def test_min_players_roundtrip_and_validation(self):
        self._write({"min_players": 2})
        self.assertEqual(cfg.load_config(self._path)["min_players"], 2)
        for bad in (0, -1, True, "2", 1.5):
            self._write({"min_players": bad})
            with self.assertRaises(cfg.ConfigError):
                cfg.load_config(self._path)

    def test_ui_dialogs_roundtrip_and_validation(self):
        self._write({"ui_dialogs": False})
        self.assertEqual(cfg.load_config(self._path)["ui_dialogs"], False)
        self.assertTrue("ui_dialogs" in cfg.DEFAULT_CONFIG)
        self._write({"ui_dialogs": "yes"})
        with self.assertRaises(cfg.ConfigError):
            cfg.load_config(self._path)
        self._write({"ui_dialogs": 0})
        with self.assertRaises(cfg.ConfigError):
            cfg.load_config(self._path)

    def test_auto_reconnect_keys_roundtrip_and_validation(self):
        self._write({
            "auto_reconnect": False,
            "reconnect_backoff_min": 3.0,
            "reconnect_backoff_max": 40.0,
        })
        loaded = cfg.load_config(self._path)
        self.assertEqual(loaded["auto_reconnect"], False)
        self.assertEqual(loaded["reconnect_backoff_min"], 3.0)
        self.assertEqual(loaded["reconnect_backoff_max"], 40.0)
        for bad in ({"auto_reconnect": "yes"}, {"reconnect_backoff_min": 0.1},
                    {"reconnect_backoff_min": True}, {"reconnect_backoff_max": -1},
                    {"reconnect_backoff_max": "fast"}, {"reconnect_backoff_min": 10.0,
                                                        "reconnect_backoff_max": 5.0}):
            self._write(bad)
            with self.assertRaises(cfg.ConfigError):
                cfg.load_config(self._path)

    def test_load_accepts_valid_presence_ttl(self):
        self._write({"presence_ttl": 12.0})
        self.assertEqual(cfg.load_config(self._path)["presence_ttl"], 12.0)

    def test_write_default_then_load_roundtrip(self):
        cfg.write_default_config(self._path)
        self.assertEqual(cfg.load_config(self._path), cfg.DEFAULT_CONFIG)

    def test_rejects_bad_port(self):
        self._write({"port": 70000})
        with self.assertRaises(cfg.ConfigError):
            cfg.load_config(self._path)
        self._write({"port": "8765"})
        with self.assertRaises(cfg.ConfigError):
            cfg.load_config(self._path)

    def test_rejects_bad_types(self):
        self._write({"auto_connect": "yes"})
        with self.assertRaises(cfg.ConfigError):
            cfg.load_config(self._path)
        self._write({"presence_interval": -1})
        with self.assertRaises(cfg.ConfigError):
            cfg.load_config(self._path)
        self._write({"presence_ttl": -1})
        with self.assertRaises(cfg.ConfigError):
            cfg.load_config(self._path)
        self._write({"presence_ttl": "30"})
        with self.assertRaises(cfg.ConfigError):
            cfg.load_config(self._path)
        self._write({"presence_ttl": True})
        with self.assertRaises(cfg.ConfigError):
            cfg.load_config(self._path)
        self._write({"name": ""})
        with self.assertRaises(cfg.ConfigError):
            cfg.load_config(self._path)
        self._write({"auto_accept_travel": "yes"})
        with self.assertRaises(cfg.ConfigError):
            cfg.load_config(self._path)
        self._write({"world_sync": "yes"})
        with self.assertRaises(cfg.ConfigError):
            cfg.load_config(self._path)
        self._write({"world_interval": -1})
        with self.assertRaises(cfg.ConfigError):
            cfg.load_config(self._path)
        self._write({"interaction_sync": "yes"})
        with self.assertRaises(cfg.ConfigError):
            cfg.load_config(self._path)
        self._write({"interaction_interval": 0})
        with self.assertRaises(cfg.ConfigError):
            cfg.load_config(self._path)

    def test_rejects_unknown_keys_and_non_object(self):
        self._write({"bogus": 1})
        with self.assertRaises(cfg.ConfigError):
            cfg.load_config(self._path)
        self._write([1, 2, 3])
        with self.assertRaises(cfg.ConfigError):
            cfg.load_config(self._path)

    def test_missing_file_is_not_config_error(self):
        missing = os.path.join(self._tmp.name, "nope.json")
        with self.assertRaises(cfg.ConfigError):
            cfg.load_config(missing)

    def test_find_explicit_path(self):
        self._write({})
        self.assertEqual(cfg.find_config_file(self._path), self._path)
        self.assertIsNone(cfg.find_config_file(os.path.join(self._tmp.name, "missing.json")))

    def test_find_through_env(self):
        self._write({})
        old_env = os.environ.get("SIM4_MP_CONFIG")
        old_profile = os.environ.get("USERPROFILE")
        try:
            os.environ["SIM4_MP_CONFIG"] = self._path
            os.environ["USERPROFILE"] = os.path.join(self._tmp.name, "phony")
            self.assertEqual(cfg.find_config_file(), self._path)
        finally:
            if old_env is None:
                os.environ.pop("SIM4_MP_CONFIG", None)
            else:
                os.environ["SIM4_MP_CONFIG"] = old_env
            if old_profile is None:
                os.environ.pop("USERPROFILE", None)
            else:
                os.environ["USERPROFILE"] = old_profile


if __name__ == "__main__":
    unittest.main()