from __future__ import annotations

import asyncio
from datetime import datetime
from logging import getLogger
import time
import re
from typing import TYPE_CHECKING

from config import SCAN_INTERVAL, SCAN_TIMEOUT, SUBNETS, ACTIVE_HOURS
from app.exceptions import NmapScanError

if TYPE_CHECKING:
    from app.watcher import Watcher

_log = getLogger(__name__)


class Tracker:
    """Tracks active devices on the network and manages user logins.

    This class periodically scans specified subnets for active devices and
    logs users in automatically based on detected devices.
    """

    _MAC_REGEX = re.compile(
        r"(\d+\.\d+\.\d+\.\d+).*?((?:[0-9A-Fa-f]{2}[:]){5}(?:[0-9A-Fa-f]{2}))",
        flags=re.DOTALL,
    )

    def __init__(self, watcher: Watcher) -> None:
        """Initializes the Tracker with a reference to the Watcher.

        Args:
            watcher (Watcher): The Watcher instance for managing user sessions.
        """
        self.watcher = watcher

    async def _scan_subnets(self, subnets: list[str]) -> dict[str, str]:
        """Scans provided subnets for active MAC addresses.

        Args:
            subnets (list[str]): List of subnets to scan.

        Returns:
            dict[str, str]: Mapping of IP addresses to MAC addresses.

        Raises:
            NmapScanError: If the Nmap scan fails.
        """
        _log.debug("Scanning subnets: %s.", ", ".join(subnets))

        process = await asyncio.create_subprocess_exec(
            "nmap",
            "-sn",
            "-n",
            *subnets,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(), timeout=SCAN_TIMEOUT
            )
        except TimeoutError:
            process.terminate()
            raise
        finally:
            await process.wait()  # Ensure cleanup

        if process.returncode != 0:
            raise NmapScanError("Nmap scan failed", process.returncode)

        return {
            address: mac for address, mac in self._MAC_REGEX.findall(stdout.decode())
        }

    async def run(self) -> None:
        """Runs the network scanner in an infinite loop.

        Periodically scans for devices and logs users in based on active MAC addresses.
        """
        _log.info("Starting the network scanner.")

        while True:
            _log.debug("Sleeping for %ds.", SCAN_INTERVAL)
            await asyncio.sleep(SCAN_INTERVAL)

            if not ACTIVE_HOURS[1] >= datetime.now().hour >= ACTIVE_HOURS[0]:
                _log.debug("We are outside of active hours. Skipping loop iteration...")
                continue

            try:
                devices = await self._scan_subnets(SUBNETS)
            except TimeoutError:
                _log.warning("Nmap scan timed out.")
                continue
            except Exception:
                _log.exception("Nmap scan raised exception.")
                continue
            else:
                self.watcher.set_seen_devices(devices)

            _log.info("Found %d devices.", len(devices))

            if not devices:
                _log.debug("Found no devices on subnets: %s.", ", ".join(SUBNETS))
                continue

            for mac in devices.values():
                user = self.watcher.get_user(mac)

                if not user:
                    continue

                _log.debug("Recognized device %s.", mac)
                user.set_last_seen(time.time())

                if not user.logged_in:
                    await self.watcher.login_user(user=user)

            await self.watcher.purge_inactive_users()
