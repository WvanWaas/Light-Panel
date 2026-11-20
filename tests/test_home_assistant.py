import json
import unittest
from pathlib import Path
try:
    import yaml
    from jinja2 import Environment
    from jinja2.nativetypes import NativeEnvironment
except ImportError:
    yaml = None

BASE = Path(__file__).resolve().parents[1]

@unittest.skipIf(yaml is None, "Install tests/requirements.txt to check HA templates")
class HomeAssistantPackageTests(unittest.TestCase):
    def setUp(self):
        class Loader(yaml.SafeLoader): pass
        Loader.add_constructor("!secret", lambda loader, node: "!secret " + loader.construct_scalar(node))
        self.package = yaml.load((BASE / "home-assistant/packages/light_panel.yaml").read_text(), Loader=Loader)
        self.examples = yaml.safe_load((BASE / "home-assistant/packages/light_panel_examples.yaml").read_text())
        self.native = NativeEnvironment()
        self.native.filters["bool"] = lambda value: value is True or str(value).lower() in ("true", "on", "yes", "1")
        self.string = Environment()
        self.string.filters["to_json"] = json.dumps

    def render_message(self, **fields):
        template = self.package["script"]["light_panel_message"]["sequence"][0]["data"]["command"]
        return self.native.from_string(template).render(**fields)

    def test_quoted_multiline_message_survives_json_and_keeps_false_and_zero(self):
        title = 'Doorbell: "someone" 🚪'
        text = "Line one\nLine two: O'Reilly \\ backslash"
        message = self.render_message(title=title, text=text, duration=0, wake=False, camera="Front door")
        body = self.string.from_string(self.package["rest_command"]["light_panel_webhook"]["payload"]).render(command=message)
        decoded = json.loads(body)
        self.assertEqual(decoded["title"], title)
        self.assertEqual(decoded["text"], text)
        self.assertEqual(decoded["duration"], 0)
        self.assertIs(decoded["wake"], False)
        self.assertEqual(decoded["camera"], "Front door")

    def test_omitted_fields_use_valid_message_defaults(self):
        result = self.render_message()
        self.assertEqual(result["action"], "message")
        self.assertEqual(result["duration"], 30)
        self.assertIs(result["wake"], True)
        self.assertEqual(result["camera"], "")

    def test_device_selection_only_adds_an_explicit_target(self):
        template = self.package["script"]["light_panel_command"]["sequence"][0]["data"]["command"]
        command = {"action": "screen_off"}
        for device in ["", "   "]:
            self.assertEqual(self.native.from_string(template).render(command=command, device=device), command)
        targeted = self.native.from_string(template).render(command=command, device=" frame-example-123 ")
        self.assertEqual(targeted, {"action": "screen_off", "device": "frame-example-123"})

    def test_non_200_response_stops_script_instead_of_silent_success(self):
        conditional = self.package["script"]["light_panel_command"]["sequence"][1]
        template = conditional["if"][0]["value_template"]
        for status in [400, 401, 409, 502, 504]:
            self.assertTrue(self.native.from_string(template).render(light_panel_response={"status": status}))
        self.assertFalse(self.native.from_string(template).render(light_panel_response={"status": 200}))
        self.assertIs(conditional["then"][0]["error"], True)

    def test_secrets_stay_external_and_examples_are_opt_in(self):
        rest = self.package["rest_command"]["light_panel_webhook"]
        self.assertEqual(rest["url"], "!secret light_panel_webhook_url")
        self.assertEqual(rest["headers"]["Authorization"], "!secret light_panel_webhook_authorization")
        automations = self.examples["automation"]
        self.assertEqual(len(automations), 7)
        self.assertTrue(all(row["initial_state"] is False for row in automations))
        self.assertEqual(len({row["id"] for row in automations}), len(automations))
        for automation in automations:
            for action in automation["actions"]:
                service = action["action"]
                self.assertIn(service.removeprefix("script."), self.package["script"])

    def test_dashboard_buttons_reference_included_scripts(self):
        view = yaml.safe_load((BASE / "home-assistant/dashboard-view.yaml").read_text())
        for section in view["sections"]:
            for card in section["cards"]:
                if card["type"] == "button":
                    service = card["tap_action"]["perform_action"]
                    self.assertIn(service.removeprefix("script."), self.package["script"])

if __name__ == "__main__": unittest.main()
