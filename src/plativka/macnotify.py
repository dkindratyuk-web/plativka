"""macOS: сповіщення «Зараз грає» з обкладинкою для віконної Платівки.

Сповіщення надсилає сама програма (Plativka Desktop.app) через системний центр
сповіщень, тому праворуч у ньому — обкладинка альбому, а в заголовку — «Платівка».
Працює лише у зібраній програмі (DMG): системі потрібен пакет .app з ідентифікатором.
Якщо щось недоступно, повертаємо False — і сповіщення покаже osascript, без обкладинки.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import uuid

_center = None
_delegate = None
_ok: bool | None = None


def _setup() -> bool:
    global _center, _delegate, _ok
    if _ok is not None:
        return _ok
    _ok = False
    if sys.platform != "darwin" or not getattr(sys, "frozen", False):
        return False
    try:
        from Foundation import NSObject
        from UserNotifications import (UNAuthorizationOptionAlert, UNAuthorizationOptionSound,
                                       UNUserNotificationCenter)

        class _Delegate(NSObject):
            # показувати банер, навіть коли Платівка попереду
            def userNotificationCenter_willPresentNotification_withCompletionHandler_(self, center, note, handler):
                handler(16 | 8)   # UNNotificationPresentationOptionBanner | List

        _center = UNUserNotificationCenter.currentNotificationCenter()
        _delegate = _Delegate.alloc().init()
        _center.setDelegate_(_delegate)
        _center.requestAuthorizationWithOptions_completionHandler_(
            UNAuthorizationOptionAlert | UNAuthorizationOptionSound, lambda granted, err: None)
        _ok = True
    except Exception:
        _ok = False
    return _ok


def init() -> bool:
    """Викликати один раз на старті (головний потік): спитати дозвіл на сповіщення."""
    return _setup()


def show(title: str, subtitle: str, body: str, image: str | None = None) -> bool:
    if not _setup():
        return False
    try:
        from Foundation import NSURL
        from UserNotifications import (UNMutableNotificationContent, UNNotificationAttachment,
                                       UNNotificationRequest)
        content = UNMutableNotificationContent.alloc().init()
        content.setTitle_(title)
        if subtitle:
            content.setSubtitle_(subtitle)
        content.setBody_(body)
        content.setThreadIdentifier_("now-playing")
        if image and os.path.exists(image):
            # система «забирає» файл вкладення собі — даємо їй окрему копію
            tmp = os.path.join(tempfile.gettempdir(), f"plativka-cover-{uuid.uuid4().hex[:8]}.jpg")
            shutil.copyfile(image, tmp)
            att, err = UNNotificationAttachment.attachmentWithIdentifier_URL_options_error_(
                "cover", NSURL.fileURLWithPath_(tmp), None, None)
            if att is not None:
                content.setAttachments_([att])
        req = UNNotificationRequest.requestWithIdentifier_content_trigger_("plativka-now-playing", content, None)
        _center.addNotificationRequest_withCompletionHandler_(req, None)
        return True
    except Exception:
        return False
