"""Check for OpenLIFU desktop application updates and present the result."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
import logging
import re
from urllib.parse import urlparse

import qt
import slicer


LATEST_RELEASE_API_URL = (
    "https://api.github.com/repos/"
    "OpenwaterHealth/openlifu-desktop-application/releases/latest"
)
GITHUB_API_VERSION = "2026-03-10"
REQUEST_TIMEOUT_MS = 10_000
SUPPRESSED_RELEASE_SETTING = "OpenLIFU/UpdateCheck/suppressedReleaseTag"

UPDATE_WIDGET_OBJECT_NAME = "OpenLIFUUpdateCheckWidget"
STATUS_LABEL_OBJECT_NAME = "OpenLIFUUpdateStatusLabel"
UPDATE_BUTTON_OBJECT_NAME = "OpenLIFUUpdateButton"
RECHECK_BUTTON_OBJECT_NAME = "OpenLIFUUpdateRecheckButton"

_FINAL_RELEASE_TAG_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
_RELEASE_PAGE_PATH_PREFIX = (
    "/OpenwaterHealth/openlifu-desktop-application/releases/tag/"
)


class UpdateCheckError(RuntimeError):
    """Raised when GitHub does not provide usable release information."""


@dataclass(frozen=True)
class ReleaseInfo:
    """Validated information about a published OpenLIFU release."""

    tag: str
    version: tuple[int, int, int]
    page_url: str


@dataclass(frozen=True)
class UpdateDialogResult:
    """Actions selected while dismissing the update-available dialog."""

    suppress: bool
    open_download_page: bool


def current_application_version() -> tuple[int, int, int]:
    """Return the numeric OpenLIFU application version exposed by Slicer."""

    return (
        int(slicer.app.mainApplicationMajorVersion),
        int(slicer.app.mainApplicationMinorVersion),
        int(slicer.app.mainApplicationPatchVersion),
    )


def version_tag(version: tuple[int, int, int]) -> str:
    """Format a numeric version tuple as an OpenLIFU release tag."""

    return "v" + ".".join(str(part) for part in version)


def parse_release_response(payload: bytes | str) -> ReleaseInfo:
    """Validate and parse a GitHub latest-release API response."""

    try:
        release = json.loads(payload)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as exc:
        raise UpdateCheckError("GitHub returned malformed release information.") from exc

    if not isinstance(release, dict):
        raise UpdateCheckError("GitHub returned malformed release information.")
    if release.get("draft") is not False or release.get("prerelease") is not False:
        raise UpdateCheckError("GitHub did not return a published stable release.")

    tag = release.get("tag_name")
    page_url = release.get("html_url")
    if not isinstance(tag, str) or not isinstance(page_url, str):
        raise UpdateCheckError("GitHub's release information is incomplete.")

    tag_match = _FINAL_RELEASE_TAG_PATTERN.fullmatch(tag)
    if tag_match is None:
        raise UpdateCheckError(f"GitHub returned an unsupported release tag: {tag!r}.")

    parsed_url = urlparse(page_url)
    expected_path = _RELEASE_PAGE_PATH_PREFIX + tag
    if (
        parsed_url.scheme != "https"
        or parsed_url.netloc.lower() != "github.com"
        or parsed_url.path != expected_path
        or parsed_url.params
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise UpdateCheckError("GitHub returned an unexpected release page URL.")

    version = tuple(int(part) for part in tag_match.groups())
    return ReleaseInfo(tag=tag, version=version, page_url=page_url)


def is_update_available(
    current_version: tuple[int, int, int],
    latest_version: tuple[int, int, int],
) -> bool:
    """Return whether the latest stable release is newer than this application."""

    return latest_version > current_version


def open_url_in_system_browser(url: str) -> bool:
    """Open an HTTPS URL using the operating system's default browser."""

    return bool(qt.QDesktopServices.openUrl(qt.QUrl(url)))


def run_update_available_dialog(
    parent,
    current_version: tuple[int, int, int],
    release: ReleaseInfo,
) -> UpdateDialogResult:
    """Display the update notification and return the user's requested actions."""

    message_box = qt.QMessageBox(parent)
    message_box.setWindowTitle("OpenLIFU update available")
    message_box.setIcon(qt.QMessageBox.Information)
    message_box.setText(
        f"OpenLIFU {release.tag} is available.\n\n"
        f"You are currently using OpenLIFU {version_tag(current_version)}."
    )

    suppress_checkbox = qt.QCheckBox("Do not show this again", message_box)
    suppress_checkbox.setChecked(False)
    message_box.setCheckBox(suppress_checkbox)

    open_button = message_box.addButton(
        "Open download page", qt.QMessageBox.AcceptRole
    )
    close_button = message_box.addButton(qt.QMessageBox.Close)
    message_box.setDefaultButton(open_button)
    message_box.setEscapeButton(close_button)

    message_box.exec()
    result = UpdateDialogResult(
        suppress=suppress_checkbox.isChecked(),
        open_download_page=message_box.clickedButton() == open_button,
    )
    message_box.deleteLater()
    return result


class GitHubReleaseClient:
    """Fetch the latest OpenLIFU release without blocking the Qt event loop."""

    def __init__(self, parent=None, network_manager=None, timeout_ms=REQUEST_TIMEOUT_MS):
        self._network_manager = network_manager or qt.QNetworkAccessManager(parent)
        self._timeout_ms = timeout_ms
        self._reply = None

    @property
    def is_checking(self) -> bool:
        return self._reply is not None

    def fetch_latest(
        self,
        on_success: Callable[[ReleaseInfo], None],
        on_failure: Callable[[str], None],
    ) -> bool:
        """Start a request and return immediately, or return False if one is active."""

        if self._reply is not None:
            return False

        request = qt.QNetworkRequest(qt.QUrl(LATEST_RELEASE_API_URL))
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        request.setRawHeader(b"X-GitHub-Api-Version", GITHUB_API_VERSION.encode())
        request.setRawHeader(b"User-Agent", b"OpenLIFU-update-check")
        request.setAttribute(
            qt.QNetworkRequest.RedirectPolicyAttribute,
            qt.QNetworkRequest.NoLessSafeRedirectPolicy,
        )
        request.setTransferTimeout(self._timeout_ms)

        reply = self._network_manager.get(request)
        self._reply = reply
        reply.finished.connect(
            lambda: self._on_reply_finished(reply, on_success, on_failure)
        )
        return True

    def _on_reply_finished(self, reply, on_success, on_failure) -> None:
        if reply != self._reply:
            reply.deleteLater()
            return

        self._reply = None
        callback = on_failure
        callback_argument = "An unknown error occurred."
        try:
            status = reply.attribute(qt.QNetworkRequest.HttpStatusCodeAttribute)
            status = int(status) if status is not None else None
            error = reply.error()

            if error != qt.QNetworkReply.NoError:
                callback_argument = self._reply_error_detail(reply, status, error)
            elif status is None or not 200 <= status < 300:
                callback_argument = (
                    f"GitHub returned HTTP {status}."
                    if status
                    else "No HTTP response was received."
                )
            else:
                release = parse_release_response(reply.readAll().data())
                callback = on_success
                callback_argument = release
        except UpdateCheckError as exc:
            callback_argument = str(exc)
        except Exception as exc:
            logging.exception("OpenLIFU update check failed")
            callback_argument = _brief_error_detail(exc)
        finally:
            reply.deleteLater()

        try:
            callback(callback_argument)
        except Exception:
            logging.exception("OpenLIFU update-check result handler failed")

    @staticmethod
    def _reply_error_detail(reply, status, error) -> str:
        if error == qt.QNetworkReply.TimeoutError:
            return "The request timed out."

        rate_limit_remaining = reply.rawHeader(b"X-RateLimit-Remaining").data()
        if status in (403, 429) and rate_limit_remaining == b"0":
            return "GitHub's request rate limit was reached."

        error_string = _brief_error_detail(reply.errorString())
        if status is not None:
            return f"GitHub returned HTTP {status}: {error_string}"
        return error_string


class UpdateCheckController:
    """Own the toolbar controls and coordinate update checks."""

    def __init__(
        self,
        toolbar,
        *,
        release_client=None,
        settings=None,
        url_opener=None,
        dialog_runner=None,
        installed_version=None,
    ):
        self.toolbar = toolbar
        self.settings = settings if settings is not None else qt.QSettings()
        self.url_opener = url_opener or open_url_in_system_browser
        self.dialog_runner = dialog_runner or run_update_available_dialog
        self.installed_version = installed_version or current_application_version()
        self.latest_release = None
        self._checking = False

        self.container = qt.QWidget(toolbar)
        self.container.setObjectName(UPDATE_WIDGET_OBJECT_NAME)
        self.layout = qt.QHBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)

        self.status_label = qt.QLabel(self.container)
        self.status_label.setObjectName(STATUS_LABEL_OBJECT_NAME)
        muted_palette = self.status_label.palette
        muted_palette.setColor(
            qt.QPalette.WindowText,
            muted_palette.color(qt.QPalette.Disabled, qt.QPalette.WindowText),
        )
        self.status_label.setPalette(muted_palette)

        self.update_button = qt.QPushButton(self.container)
        self.update_button.setObjectName(UPDATE_BUTTON_OBJECT_NAME)
        update_button_font = self.update_button.font
        update_button_font.setBold(True)
        self.update_button.setFont(update_button_font)
        self.update_button.clicked.connect(self._on_update_button_clicked)

        self.recheck_button = qt.QToolButton(self.container)
        self.recheck_button.setObjectName(RECHECK_BUTTON_OBJECT_NAME)
        self.recheck_button.setAutoRaise(True)
        self.recheck_button.setIcon(
            slicer.app.style().standardIcon(qt.QStyle.SP_BrowserReload)
        )
        self.recheck_button.setAccessibleName("Check for OpenLIFU updates")
        self.recheck_button.setToolTip("Check for OpenLIFU updates again")
        self.recheck_button.clicked.connect(self._on_recheck_button_clicked)

        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.update_button)
        self.layout.addWidget(self.recheck_button)
        self.toolbar.addWidget(self.container)

        self.release_client = release_client or GitHubReleaseClient(self.container)
        self._show_checking_state()

    @property
    def is_checking(self) -> bool:
        return self._checking

    def check_for_updates(self, *, show_dialog: bool) -> bool:
        """Start an update check, returning without waiting for its result."""

        if self._checking:
            return False

        self._checking = True
        self._show_checking_state()
        try:
            started = self.release_client.fetch_latest(
                lambda release: self._on_check_succeeded(release, show_dialog),
                self._on_check_failed,
            )
        except Exception as exc:
            logging.exception("Could not start the OpenLIFU update check")
            self._on_check_failed(_brief_error_detail(exc))
            return False
        if not started:
            self._on_check_failed("An update check is already in progress.")
        return started

    def _on_check_succeeded(self, release: ReleaseInfo, show_dialog: bool) -> None:
        self._checking = False
        self.latest_release = release
        self.recheck_button.setEnabled(True)

        if is_update_available(self.installed_version, release.version):
            self._show_update_available_state(release)
            if show_dialog:
                self._maybe_show_update_dialog(release)
        else:
            self._show_up_to_date_state(release)

    def _on_check_failed(self, detail: str) -> None:
        self._checking = False
        self.latest_release = None
        self._show_failure_state(detail)

    def _show_checking_state(self) -> None:
        self.status_label.setText("Checking for updates...")
        self.status_label.setToolTip(
            "The update check is running in the background."
        )
        self.status_label.setVisible(True)
        self.update_button.setVisible(False)
        self.recheck_button.setEnabled(False)

    def _show_up_to_date_state(self, release: ReleaseInfo) -> None:
        installed_tag = version_tag(self.installed_version)
        self.status_label.setText(f"OpenLIFU {installed_tag} is up to date")
        if self.installed_version == release.version:
            tooltip = f"You are using the latest OpenLIFU release ({release.tag})."
        else:
            tooltip = (
                f"Installed version: {installed_tag}. "
                f"Latest stable release: {release.tag}."
            )
        self.status_label.setToolTip(tooltip)
        self.status_label.setVisible(True)
        self.update_button.setVisible(False)
        self.recheck_button.setEnabled(True)

    def _show_update_available_state(self, release: ReleaseInfo) -> None:
        self.status_label.setVisible(False)
        self.update_button.setText(f"Update to {release.tag}")
        self.update_button.setToolTip(
            f"Open the OpenLIFU {release.tag} release page in your default web browser."
        )
        self.update_button.setVisible(True)
        self.recheck_button.setEnabled(True)

    def _show_failure_state(self, detail: str) -> None:
        self.status_label.setText("Unable to check for updates")
        self.status_label.setToolTip(
            f"Unable to check for updates: {_brief_error_detail(detail)}"
        )
        self.status_label.setVisible(True)
        self.update_button.setVisible(False)
        self.recheck_button.setEnabled(True)

    def _maybe_show_update_dialog(self, release: ReleaseInfo) -> None:
        suppressed_release = str(
            self.settings.value(SUPPRESSED_RELEASE_SETTING, "")
        )
        if suppressed_release == release.tag:
            return

        result = self.dialog_runner(
            slicer.util.mainWindow(), self.installed_version, release
        )
        if result.suppress:
            self.settings.setValue(SUPPRESSED_RELEASE_SETTING, release.tag)
            self.settings.sync()
            if (
                hasattr(self.settings, "status")
                and self.settings.status() != qt.QSettings.NoError
            ):
                logging.warning(
                    "Could not save the OpenLIFU update-notification preference"
                )
        if result.open_download_page:
            self._open_release_page(release.page_url)

    def _open_release_page(self, url: str) -> None:
        if not self.url_opener(url):
            logging.warning("Could not open the OpenLIFU release page: %s", url)

    def _on_update_button_clicked(self, checked=False) -> None:
        del checked
        if self.latest_release is not None:
            self._open_release_page(self.latest_release.page_url)

    def _on_recheck_button_clicked(self, checked=False) -> None:
        del checked
        self.check_for_updates(show_dialog=False)


def _brief_error_detail(detail) -> str:
    text = " ".join(str(detail).split())
    if not text:
        return "An unknown error occurred."
    return text[:200]


_controller = None


def inject_update_widget():
    """Inject and start the update checker after normal GUI startup."""

    global _controller

    if slicer.app.testingEnabled() or slicer.app.commandOptions().noMainWindow:
        return None
    if _controller is not None:
        try:
            if _controller.container.objectName == UPDATE_WIDGET_OBJECT_NAME:
                return _controller
        except RuntimeError:
            _controller = None

    main_window = slicer.util.mainWindow()
    if main_window is None:
        logging.warning("Cannot add the OpenLIFU update checker without a main window")
        return None

    try:
        toolbar = slicer.util.findChild(main_window, "CustomToolBar")
    except (IndexError, RuntimeError):
        logging.warning("Cannot find CustomToolBar for the OpenLIFU update checker")
        return None

    existing_widget = toolbar.findChild("QWidget", UPDATE_WIDGET_OBJECT_NAME)
    if existing_widget is not None:
        return None

    _controller = UpdateCheckController(toolbar)
    _controller.check_for_updates(show_dialog=True)
    return _controller
