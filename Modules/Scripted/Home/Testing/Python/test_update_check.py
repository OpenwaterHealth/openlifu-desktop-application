"""Tests for the OpenLIFU application update checker."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import qt
import slicer


HOME_MODULE_DIR = Path(__file__).resolve().parents[2]
if str(HOME_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(HOME_MODULE_DIR))

from HomeLib import update_check


RELEASE_1_12_1 = update_check.ReleaseInfo(
    tag="v1.12.1",
    version=(1, 12, 1),
    page_url=(
        "https://github.com/OpenwaterHealth/"
        "openlifu-desktop-application/releases/tag/v1.12.1"
    ),
)
RELEASE_1_13_0 = update_check.ReleaseInfo(
    tag="v1.13.0",
    version=(1, 13, 0),
    page_url=(
        "https://github.com/OpenwaterHealth/"
        "openlifu-desktop-application/releases/tag/v1.13.0"
    ),
)


class FakeReleaseClient:
    """Capture asynchronous release callbacks for deterministic completion."""

    def __init__(self):
        self.fetch_count = 0
        self._callbacks = None

    def fetch_latest(self, on_success, on_failure):
        if self._callbacks is not None:
            return False
        self.fetch_count += 1
        self._callbacks = (on_success, on_failure)
        return True

    def succeed(self, release):
        if self._callbacks is None:
            raise AssertionError("No update check is in progress")
        on_success, _ = self._callbacks
        self._callbacks = None
        on_success(release)

    def fail(self, detail):
        if self._callbacks is None:
            raise AssertionError("No update check is in progress")
        _, on_failure = self._callbacks
        self._callbacks = None
        on_failure(detail)


class MemorySettings:
    def __init__(self):
        self.values = {}
        self.sync_count = 0

    def value(self, key, default=None):
        return self.values.get(key, default)

    def setValue(self, key, value):
        self.values[key] = value

    def sync(self):
        self.sync_count += 1


class FakeSignal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback

    def emit(self):
        if self.callback is None:
            raise AssertionError("Signal has no callback")
        self.callback()


class FakeByteArray:
    def __init__(self, value):
        self.value = value

    def data(self):
        return self.value


class FakeNetworkReply:
    def __init__(self, payload, *, status=200, error=None, error_string=""):
        self.finished = FakeSignal()
        self.payload = payload
        self.status = status
        self.network_error = (
            qt.QNetworkReply.NoError if error is None else error
        )
        self.error_string = error_string
        self.rate_limit_remaining = b"1"
        self.deleted = False

    def attribute(self, attribute):
        if attribute != qt.QNetworkRequest.HttpStatusCodeAttribute:
            raise AssertionError(f"Unexpected attribute: {attribute}")
        return self.status

    def error(self):
        return self.network_error

    def errorString(self):
        return self.error_string

    def rawHeader(self, header):
        if header != b"X-RateLimit-Remaining":
            raise AssertionError(f"Unexpected header: {header!r}")
        return FakeByteArray(self.rate_limit_remaining)

    def readAll(self):
        return FakeByteArray(self.payload)

    def deleteLater(self):
        self.deleted = True


class FakeNetworkManager:
    def __init__(self, reply):
        self.reply = reply
        self.requests = []

    def get(self, request):
        self.requests.append(request)
        return self.reply


class UpdateCheckTest(unittest.TestCase):
    def setUp(self):
        self.toolbars = []
        self.controllers = []

    def tearDown(self):
        for controller in self.controllers:
            controller.update_button.clicked.disconnect(
                controller._on_update_button_clicked
            )
            controller.recheck_button.clicked.disconnect(
                controller._on_recheck_button_clicked
            )
        for toolbar in self.toolbars:
            toolbar.clear()
            toolbar.close()
            toolbar.deleteLater()
        self.controllers.clear()
        self.toolbars.clear()
        qt.QApplication.sendPostedEvents(None, qt.QEvent.DeferredDelete)
        slicer.app.processEvents()

    def make_controller(
        self,
        *,
        release_client=None,
        settings=None,
        url_opener=None,
        dialog_runner=None,
        installed_version=(1, 12, 0),
    ):
        toolbar = qt.QToolBar()
        self.toolbars.append(toolbar)
        controller = update_check.UpdateCheckController(
            toolbar,
            release_client=release_client or FakeReleaseClient(),
            settings=settings or MemorySettings(),
            url_opener=url_opener or (lambda _url: True),
            dialog_runner=dialog_runner
            or (
                lambda _parent, _current_version, _release: (
                    update_check.UpdateDialogResult(False, False)
                )
            ),
            installed_version=installed_version,
        )
        self.controllers.append(controller)
        return controller

    def test_parse_release_response_and_compare_versions(self):
        payload = json.dumps(
            {
                "draft": False,
                "prerelease": False,
                "tag_name": RELEASE_1_12_1.tag,
                "html_url": RELEASE_1_12_1.page_url,
            }
        ).encode()

        self.assertEqual(
            update_check.parse_release_response(payload), RELEASE_1_12_1
        )
        self.assertTrue(
            update_check.is_update_available((1, 12, 0), (1, 12, 1))
        )
        self.assertFalse(
            update_check.is_update_available((1, 12, 1), (1, 12, 1))
        )
        self.assertFalse(
            update_check.is_update_available((1, 13, 0), (1, 12, 1))
        )
        self.assertEqual(update_check.version_tag((1, 12, 1)), "v1.12.1")

    def test_parse_release_response_rejects_unusable_responses(self):
        valid_release = {
            "draft": False,
            "prerelease": False,
            "tag_name": RELEASE_1_12_1.tag,
            "html_url": RELEASE_1_12_1.page_url,
        }
        invalid_responses = [
            b"not JSON",
            json.dumps([]),
            json.dumps({**valid_release, "draft": True}),
            json.dumps({**valid_release, "prerelease": True}),
            json.dumps({**valid_release, "tag_name": "v1.12.1-rc1"}),
            json.dumps(
                {
                    **valid_release,
                    "html_url": "https://example.com/releases/tag/v1.12.1",
                }
            ),
        ]

        for payload in invalid_responses:
            with self.subTest(payload=payload):
                with self.assertRaises(update_check.UpdateCheckError):
                    update_check.parse_release_response(payload)

    def test_current_application_version_uses_numeric_properties(self):
        fake_slicer = SimpleNamespace(
            app=SimpleNamespace(
                mainApplicationMajorVersion="2",
                mainApplicationMinorVersion="3",
                mainApplicationPatchVersion="4",
                applicationVersion="2.3.4-2099-12-31",
            )
        )

        with mock.patch.object(update_check, "slicer", fake_slicer):
            self.assertEqual(update_check.current_application_version(), (2, 3, 4))

    def test_github_client_returns_immediately_and_parses_reply(self):
        payload = json.dumps(
            {
                "draft": False,
                "prerelease": False,
                "tag_name": RELEASE_1_12_1.tag,
                "html_url": RELEASE_1_12_1.page_url,
            }
        ).encode()
        reply = FakeNetworkReply(payload)
        network_manager = FakeNetworkManager(reply)
        client = update_check.GitHubReleaseClient(
            network_manager=network_manager,
            timeout_ms=1234,
        )
        successes = []
        failures = []

        self.assertTrue(client.fetch_latest(successes.append, failures.append))
        self.assertTrue(client.is_checking)
        self.assertEqual(successes, [])
        self.assertEqual(failures, [])
        self.assertFalse(client.fetch_latest(successes.append, failures.append))

        request = network_manager.requests[0]
        self.assertEqual(
            request.url().toString(), update_check.LATEST_RELEASE_API_URL
        )
        self.assertEqual(
            request.rawHeader(b"Accept").data(),
            b"application/vnd.github+json",
        )
        self.assertEqual(
            request.rawHeader(b"X-GitHub-Api-Version").data(),
            update_check.GITHUB_API_VERSION.encode(),
        )
        self.assertEqual(
            request.rawHeader(b"User-Agent").data(), b"OpenLIFU-update-check"
        )
        self.assertEqual(request.transferTimeout(), 1234)

        reply.finished.emit()
        self.assertFalse(client.is_checking)
        self.assertEqual(successes, [RELEASE_1_12_1])
        self.assertEqual(failures, [])
        self.assertTrue(reply.deleted)

    def test_github_client_does_not_reclassify_result_handler_errors(self):
        payload = json.dumps(
            {
                "draft": False,
                "prerelease": False,
                "tag_name": RELEASE_1_12_1.tag,
                "html_url": RELEASE_1_12_1.page_url,
            }
        ).encode()
        reply = FakeNetworkReply(payload)
        client = update_check.GitHubReleaseClient(
            network_manager=FakeNetworkManager(reply)
        )
        failures = []

        def failing_success_handler(_release):
            raise RuntimeError("UI callback failed")

        self.assertTrue(client.fetch_latest(failing_success_handler, failures.append))
        with self.assertLogs(level="ERROR"):
            reply.finished.emit()

        self.assertEqual(failures, [])
        self.assertFalse(client.is_checking)
        self.assertTrue(reply.deleted)

    def test_github_client_reports_timeout_and_rate_limit(self):
        cases = [
            (
                FakeNetworkReply(
                    b"",
                    status=None,
                    error=qt.QNetworkReply.TimeoutError,
                    error_string="Operation canceled",
                ),
                "The request timed out.",
            ),
            (
                FakeNetworkReply(
                    b"",
                    status=403,
                    error=qt.QNetworkReply.ContentAccessDenied,
                    error_string="Forbidden",
                ),
                "GitHub's request rate limit was reached.",
            ),
        ]
        cases[1][0].rate_limit_remaining = b"0"

        for reply, expected_detail in cases:
            with self.subTest(expected_detail=expected_detail):
                client = update_check.GitHubReleaseClient(
                    network_manager=FakeNetworkManager(reply)
                )
                failures = []
                self.assertTrue(client.fetch_latest(self.fail, failures.append))
                reply.finished.emit()
                self.assertEqual(failures, [expected_detail])
                self.assertTrue(reply.deleted)

    def test_update_dialog_result_covers_every_dismissal_path(self):
        class FakeCheckBox:
            instances = []

            def __init__(self, text, parent):
                self.text = text
                self.parent = parent
                self.checked = None
                self.__class__.instances.append(self)

            def setChecked(self, checked):
                self.checked = checked

            def isChecked(self):
                return self.checked

        class FakeMessageBox:
            Information = 1
            AcceptRole = 2
            Close = 3
            next_action = "close"
            next_suppress = False
            checkbox_started_unchecked = []

            def __init__(self, parent):
                self.parent = parent
                self.checkbox = None
                self.open_button = object()
                self.close_button = object()
                self.clicked_button = None
                self.deleted = False

            def setWindowTitle(self, _title):
                pass

            def setIcon(self, _icon):
                pass

            def setText(self, _text):
                pass

            def setCheckBox(self, checkbox):
                self.checkbox = checkbox

            def addButton(self, button_or_text, _role=None):
                if button_or_text == "Open download page":
                    return self.open_button
                return self.close_button

            def setDefaultButton(self, _button):
                pass

            def setEscapeButton(self, _button):
                pass

            def exec(self):
                self.checkbox_started_unchecked.append(
                    self.checkbox.checked is False
                )
                self.checkbox.checked = self.next_suppress
                if self.next_action == "open":
                    self.clicked_button = self.open_button
                elif self.next_action == "close":
                    self.clicked_button = self.close_button
                else:
                    self.clicked_button = None

            def clickedButton(self):
                return self.clicked_button

            def deleteLater(self):
                self.deleted = True

        outcomes = [
            ("open", True, update_check.UpdateDialogResult(True, True)),
            ("close", True, update_check.UpdateDialogResult(True, False)),
            ("window-x", True, update_check.UpdateDialogResult(True, False)),
            ("close", False, update_check.UpdateDialogResult(False, False)),
        ]

        with (
            mock.patch.object(update_check.qt, "QMessageBox", FakeMessageBox),
            mock.patch.object(update_check.qt, "QCheckBox", FakeCheckBox),
        ):
            for action, suppress, expected_result in outcomes:
                with self.subTest(action=action, suppress=suppress):
                    FakeMessageBox.next_action = action
                    FakeMessageBox.next_suppress = suppress
                    result = update_check.run_update_available_dialog(
                        None, (1, 12, 0), RELEASE_1_12_1
                    )
                    self.assertEqual(result, expected_result)
                    self.assertTrue(FakeMessageBox.checkbox_started_unchecked[-1])

    def test_async_states_and_duplicate_in_flight_check(self):
        client = FakeReleaseClient()
        controller = self.make_controller(
            release_client=client,
            installed_version=RELEASE_1_12_1.version,
        )

        self.assertTrue(controller.check_for_updates(show_dialog=True))
        self.assertTrue(controller.is_checking)
        self.assertEqual(controller.status_label.text, "Checking for updates...")
        self.assertFalse(controller.recheck_button.enabled)

        self.assertFalse(controller.check_for_updates(show_dialog=True))
        self.assertEqual(client.fetch_count, 1)
        self.assertTrue(controller.is_checking)

        client.succeed(RELEASE_1_12_1)
        self.assertFalse(controller.is_checking)
        self.assertEqual(
            controller.status_label.text,
            "OpenLIFU v1.12.1 is up to date",
        )
        self.assertFalse(controller.status_label.isHidden())
        self.assertTrue(controller.update_button.isHidden())
        self.assertTrue(controller.recheck_button.enabled)

    def test_startup_check_shows_dialog_but_manual_recheck_does_not(self):
        client = FakeReleaseClient()
        dialog_calls = []

        def dialog_runner(parent, current_version, release):
            dialog_calls.append((parent, current_version, release))
            return update_check.UpdateDialogResult(False, False)

        controller = self.make_controller(
            release_client=client,
            dialog_runner=dialog_runner,
        )

        self.assertTrue(controller.check_for_updates(show_dialog=True))
        client.succeed(RELEASE_1_12_1)
        self.assertEqual(len(dialog_calls), 1)
        self.assertEqual(dialog_calls[0][1:], ((1, 12, 0), RELEASE_1_12_1))

        controller.recheck_button.click()
        self.assertEqual(client.fetch_count, 2)
        client.succeed(RELEASE_1_12_1)
        self.assertEqual(len(dialog_calls), 1)

    def test_dialog_and_update_button_open_release_page(self):
        client = FakeReleaseClient()
        opened_urls = []

        controller = self.make_controller(
            release_client=client,
            url_opener=lambda url: opened_urls.append(url) or True,
            dialog_runner=lambda _parent, _current_version, _release: (
                update_check.UpdateDialogResult(False, True)
            ),
        )

        controller.check_for_updates(show_dialog=True)
        client.succeed(RELEASE_1_12_1)
        self.assertEqual(opened_urls, [RELEASE_1_12_1.page_url])
        self.assertEqual(controller.update_button.text, "Update to v1.12.1")
        self.assertFalse(controller.update_button.isHidden())

        controller.update_button.click()
        self.assertEqual(
            opened_urls,
            [RELEASE_1_12_1.page_url, RELEASE_1_12_1.page_url],
        )

    def test_dialog_suppression_is_persisted_for_only_one_release(self):
        client = FakeReleaseClient()
        dialog_calls = []

        with tempfile.TemporaryDirectory() as temporary_directory:
            settings = qt.QSettings(
                str(Path(temporary_directory) / "settings.ini"),
                qt.QSettings.IniFormat,
            )

            def dialog_runner(_parent, _current_version, release):
                dialog_calls.append(release.tag)
                return update_check.UpdateDialogResult(
                    suppress=release == RELEASE_1_12_1,
                    open_download_page=False,
                )

            controller = self.make_controller(
                release_client=client,
                settings=settings,
                dialog_runner=dialog_runner,
            )

            controller.check_for_updates(show_dialog=True)
            client.succeed(RELEASE_1_12_1)
            self.assertEqual(dialog_calls, ["v1.12.1"])
            self.assertEqual(
                settings.value(update_check.SUPPRESSED_RELEASE_SETTING, ""),
                "v1.12.1",
            )

            controller.check_for_updates(show_dialog=True)
            client.succeed(RELEASE_1_12_1)
            self.assertEqual(dialog_calls, ["v1.12.1"])

            controller.check_for_updates(show_dialog=True)
            client.succeed(RELEASE_1_13_0)
            self.assertEqual(dialog_calls, ["v1.12.1", "v1.13.0"])

            settings.sync()

    def test_failure_state_contains_brief_detail(self):
        client = FakeReleaseClient()
        controller = self.make_controller(release_client=client)

        controller.check_for_updates(show_dialog=True)
        client.fail("  Network connection\nwas lost.  ")

        self.assertFalse(controller.is_checking)
        self.assertIsNone(controller.latest_release)
        self.assertEqual(
            controller.status_label.text, "Unable to check for updates"
        )
        self.assertIn(
            "Unable to check for updates: Network connection was lost.",
            controller.status_label.toolTip,
        )
        self.assertNotIn("\n", controller.status_label.toolTip)
        self.assertFalse(controller.status_label.isHidden())
        self.assertTrue(controller.update_button.isHidden())
        self.assertTrue(controller.recheck_button.enabled)


if __name__ == "__main__":
    unittest.main()
