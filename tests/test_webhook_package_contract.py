import os
import unittest
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import frameo_remote

class WebhookPackageContractTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(frameo_remote.router)
        self.client = TestClient(app)
        self.token = "light-panel-test-token-with-at-least-32-characters"
        self.headers = {"Authorization": "Bearer " + self.token}
        self.env = patch.dict(os.environ, {"FRAMEO_WEBHOOK_TOKEN": self.token})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_missing_authorization_never_relays(self):
        with patch.object(frameo_remote, "relay_frames", new_callable=AsyncMock) as relay:
            response = self.client.post("/api/frameo/webhook", json={"action": "screen_off"})
        self.assertEqual(response.status_code, 401)
        relay.assert_not_awaited()

    def test_package_screen_command_broadcasts_to_hardware(self):
        with patch.object(frameo_remote, "relay_frames", new_callable=AsyncMock, return_value={"ok": True}) as relay:
            response = self.client.post("/api/frameo/webhook", headers=self.headers, json={"action": "screen_off"})
        self.assertEqual(response.status_code, 200)
        relay.assert_awaited_once_with({"action": "screen_off"})

    def test_optional_device_targets_only_that_frame(self):
        with patch.object(frameo_remote, "relay", new_callable=AsyncMock, return_value={"ok": True}) as relay:
            response = self.client.post("/api/frameo/webhook", headers=self.headers,
                json={"action": "screen_on", "device": "frame-example-123"})
        self.assertEqual(response.status_code, 200)
        relay.assert_awaited_once_with("frame-example-123", {"action": "screen_on"})

    def test_message_camera_zero_duration_and_no_wake_are_preserved(self):
        message = {"action": "message", "title": 'Someone said "hi"', "text": "Line one\nLine two",
            "icon": "doorbell", "color": "#338cc7", "duration": 0, "wake": False,
            "camera": "Front door", "camera_crop": "left", "badge": ""}
        with patch.object(frameo_remote, "MESSAGE_CAMERAS", {"Front door": "camera.example_frontdoor"}), \
             patch.object(frameo_remote, "relay_frames", new_callable=AsyncMock, return_value={"ok": True}) as relay:
            response = self.client.post("/api/frameo/webhook", headers=self.headers, json=message)
        self.assertEqual(response.status_code, 200, response.text)
        relay.assert_awaited_once_with(message)

    def test_arbitrary_commands_and_unconfigured_cameras_are_rejected(self):
        for body in [{"action": "shell", "command": "id"},
                     {"action": "message", "title": "Test", "camera": "unconfigured"}]:
            response = self.client.post("/api/frameo/webhook", headers=self.headers, json=body)
            self.assertEqual(response.status_code, 400)

if __name__ == "__main__": unittest.main()
