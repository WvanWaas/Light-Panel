import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from settings import BASE, load_config
from site_status import SiteMonitor

class StarterTests(unittest.TestCase):
    def test_empty_install_has_no_private_integrations(self):
        with patch.dict(os.environ, {"CONFIG_PATH": "/nonexistent/light-panel.json"}):
            cfg = load_config()
        self.assertEqual(cfg["cameras"], {})
        self.assertEqual(cfg["actions"], {})
        self.assertEqual(cfg["websites"], [])
        self.assertEqual(cfg["battery"], "")

    def test_local_settings_replace_starter(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({"battery": "sensor.my_battery"}))
            with patch.dict(os.environ, {"CONFIG_PATH": str(path)}):
                self.assertEqual(load_config(), {"battery": "sensor.my_battery"})

    def test_website_monitor_only_checks_configured_domains(self):
        self.assertEqual(SiteMonitor().payload(), {"sites": []})
        self.assertEqual(SiteMonitor(domains=["example.org"]).payload()["sites"][0]["domain"], "example.org")

    def test_examples_are_valid_json(self):
        cfg = json.loads((BASE / "config.example.json").read_text())
        self.assertTrue(all(x.startswith("camera.example_") for x in cfg["cameras"].values()))
        self.assertEqual(cfg["websites"], [])

if __name__ == "__main__": unittest.main()
