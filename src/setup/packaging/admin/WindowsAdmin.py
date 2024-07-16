import ctypes
import os
import sys
from logging import Logger

from src.common.RestrictCallers import only_accept_callers_from
from src.common.ThreadLocalLogger import get_current_logger
from src.setup.packaging.admin.OSAdmin import OSAdmin
from src.setup.packaging.admin.AdminPrivilegeProvider import AdminPrivilegeProvider


class WindowsAdmin(OSAdmin):

    def is_currently_running_with_admin(self) -> bool:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            return False

    @only_accept_callers_from(AdminPrivilegeProvider)
    def provide_admin_privilege(self) -> None:

        logger: Logger = get_current_logger()

        if not self.is_currently_running_with_admin():
            logger.info("Script is not running with admin privileges. Attempting to relaunch with admin privileges...")
            # Re-launch the script with admin privileges
            try:
                script = os.path.abspath(sys.argv[0])
                params = ' '.join([script] + sys.argv[1:])
                executable_path: str = self._get_python_3_10_in_venv(sys.executable)
                ctypes.windll.shell32.ShellExecuteW(None, "runas", executable_path, params, None, 1)
                sys.exit(0)
            except Exception as e:
                # logger.error(f"Failed to relaunch script with admin privileges: {e}")
                sys.exit(1)
        else:
            logger.warning("Script is already running with root privileges.")
