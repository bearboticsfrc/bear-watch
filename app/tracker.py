from __future__ import annotations

import asyncio
from logging import getLogger
import time
from re import compile
from typing import TYPE_CHECKING

from config import SCAN_INTERVAL, SCAN_TIMEOUT, SUBNETS
from app.exceptions import NmapScanError

if TYPE_CHECKING:
    from app.watcher import Watcher

_log = getLogger(__name__)


class Tracker:
    """Tracks active devices on the network and manages user logins.

    This class periodically scans specified subnets for active devices and
    logs users in automatically based on detected devices.
    """

    _MAC_REGEX = compile(r"(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})")

    def __init__(self, watcher: Watcher) -> None:
        """Initializes the Tracker with a reference to the Watcher.

        Args:
            watcher (Watcher): The Watcher instance for managing user sessions.
        """
        self.watcher = watcher

    async def _scan_subnets(self, subnets: list[str]) -> list[str]:
        """Scans provided subnets for active MAC addresses.

        Args:
            subnets (list[str]): List of subnets to scan.

        Returns:
            list[str]: List of MAC addresses found in the scan.

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

        return self._MAC_REGEX.findall(stdout.decode())

    async def run(self) -> None:
        """Runs the network scanner in an infinite loop.

        Periodically scans for devices and logs users in based on active MAC addresses.
        """
        _log.info("Starting the network scanner.")

        while True:
            _log.debug("Sleeping for %ds.", SCAN_INTERVAL)
            await asyncio.sleep(SCAN_INTERVAL)

            try:
                devices = await self._scan_subnets(SUBNETS)
            except TimeoutError:
                _log.warning("Nmap scan timed out.")
                continue
            except Exception:
                _log.exception("Nmap scan raised exception.")
                continue

            _log.info("Found %d devices.", len(devices))

            if not devices:
                _log.debug("Found no devices on subnets: %s.", ", ".join(SUBNETS))
                continue

            for mac in devices:
                user = self.watcher.get_user(mac)

                if not user:
                    continue

                _log.debug("Recognized device %s.", mac)
                user.set_last_seen(time.time())

                if not user.logged_in:
                    await self.watcher.login_user(user=user)

            await self.watcher.purge_inactive_users()
