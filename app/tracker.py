from __future__ import annotations

import asyncio
from logging import getLogger
import time
from re import compile
from typing import TYPE_CHECKING
import functools
from scapy.layers.l2 import arping

from config import HOST_RESPONSE_TIMEOUT, SCAN_INTERVAL, SUBNETS

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

    async def _scan_network(self, network: str) -> list[str]:
        """Scans a specific network for active MAC addresses.

        This method performs an ARP scan on the specified network to identify
        devices present on the network. It uses the `arping` function from Scapy
        to send ARP requests and receives responses.

        Args:
            network (str): The network to scan, specified in CIDR notation,
                        e.g., '192.168.1.0/24'.

        Returns:
            list[str]: A list of MAC addresses (uppercased) found in the scan.
                        If no devices are found, an empty list is returned.

        Raises:
            Exception: Any exceptions raised during the ARP scanning process
                    are captured and logged.
        """
        loop = asyncio.get_event_loop()

        func = functools.partial(
            arping, net=network, timeout=HOST_RESPONSE_TIMEOUT, verbose=False
        )
        answered, _ = await loop.run_in_executor(None, func)

        return [received.hwsrc.upper() for _, received in answered]

    async def _scan_subnets(self, subnets: list[str]) -> list[str]:
        """Scans provided subnets for active MAC addresses.

        Args:
            subnets (list[str]): List of subnets to scan.

        Returns:
            list[str]: List of MAC addresses found in the scan.
        """
        _log.debug("Scanning subnets: %s.", ", ".join(subnets))

        results = await asyncio.gather(
            *[self._scan_network(network) for network in subnets],
            return_exceptions=True,
        )

        devices = []

        for result in results:
            if isinstance(result, Exception):
                _log.error("Error during network scan: %s", result)
            else:
                devices.extend(result)

        return devices

    async def run(self) -> None:
        """Runs the network scanner in an infinite loop.

        Periodically scans for devices and logs users in based on active MAC addresses.
        """
        _log.info("Starting the network scanner.")

        while True:
            _log.debug("Sleeping for %ds.", SCAN_INTERVAL)
            await asyncio.sleep(SCAN_INTERVAL)

            devices = await self._scan_subnets(SUBNETS)
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
