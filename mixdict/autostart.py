"""Manage startup running."""

import logging
import sys

from mixdict import config

logger = logging.getLogger(__name__)

if not getattr(sys, "frozen", False):
    SUPPORTED = False
    logger.info("Startup running is only supported in frozen executables")

elif sys.platform == "win32":

    import winreg

    SUPPORTED = True

    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    STARTUP_APPROVED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"

    STARTUP_ENABLE_VALUE = bytes((
        0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
    ))
    STARTUP_DISABLE_VALUE = bytes((
        0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
    ))
    STARTUP_DISABLE_FUTURE_TIME_VALUE = bytes((
        0x03, 0x00, 0x00, 0x00, 0x00, 0xc0, 0x3a, 0x43, 0xdd, 0x52, 0xc7, 0x24
    ))

    def is_enabled() -> bool | None:
        """Query whether enabled startup run.
        
        Return `None` if the status unknown or failed to query.
        """

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                RUN_KEY, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, config.APP_NAME)
        except FileNotFoundError:
            return False

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                STARTUP_APPROVED_KEY, 0, winreg.KEY_READ) as key:
                data, _ =winreg.QueryValueEx(key, config.APP_NAME)
            if isinstance(data, bytes):
                if data[0] == 0x02:
                    return True
                else:
                    return False
            else:
                return None
        except FileNotFoundError:
            return False
        except Exception:
            logger.exception("Failed to query startup run status")
            return None

    def enable() -> bool:
        """Enable startup run and return whether set successfully."""

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, config.APP_NAME, 0, winreg.REG_SZ,
                                  f'"{sys.executable}" --hidden')

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                STARTUP_APPROVED_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, config.APP_NAME, 0, winreg.REG_BINARY, STARTUP_ENABLE_VALUE)

            return True

        except Exception:
            logger.exception("Failed to set startup run")
            return False

    def disable() -> bool:
        """Disable startup run and return whether set successfully."""

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                RUN_KEY, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, config.APP_NAME)

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                STARTUP_APPROVED_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, config.APP_NAME, 0,
                                  winreg.REG_BINARY, STARTUP_DISABLE_FUTURE_TIME_VALUE)

            return True

        except FileNotFoundError:
            logger.error(f"{config.APP_NAME!r} startup item not found")
            return False
        except Exception:
            logger.exception("Failed to disable startup run")
            return False

else:
    SUPPORTED = False
    logger.warning("Currently not supported platform: %r", sys.platform)