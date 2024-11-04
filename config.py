import logging

# LOGGING_LEVEL: Specifies the logging level for the application.
# See https://docs.python.org/3/library/logging.html#logging-levels for more information.
LOGGING_LEVEL = logging.INFO

# LOGGING_FORMATTER: The formatter the applicaiton will use for logging.
# See https://docs.python.org/3/library/logging.html#logrecord-attributes for more information.
LOGGING_FORMATTER = logging.Formatter(
    "%(asctime)s - %(name)s.%(funcName)s - %(levelname)s - %(message)s"
)

# DATABASE: The file path to the SQLite database used for storing user information.
DATABASE = "app/db/users.db"

# SUBNETS: A list of subnet ranges to be scanned by Nmap to detect active devices.
# Each subnet is specified in a format recognized by Nmap. For example, "192.168.0.*" means
# all devices in the "192.168.0.x" IP range will be scanned.
SUBNETS = ("192.168.0.*",)

# ACTIVE_HOURS: A range of hours (in 24-hour format) when the scanner will be active.
# If the scanner finds we are outside of active hours, it will effectively "hibernate" and stop performing all related routines.
# Values are set in 24-hour format; e.g., 22 means 10:00 PM.
ACTIVE_HOURS = range(15, 21)

# SCAN_INTERVAL: The interval, in seconds, between each scan of the network.
# This value controls how frequently the network is scanned for user devices.
SCAN_INTERVAL = 60

# SCAN_TIMEOUT: The maximum time, in seconds, to wait for the network scan to complete.
# If the scan exceeds this time, it will be considered a timeout.
SCAN_TIMEOUT = 45

# DEBOUNCE_SECONDS: The debounce time threshold, in seconds, to determine user inactivity.
# If a user is not detected on the network within this time frame, they will be logged out.
# It is recommended to be quite high, as Nmap will often not see some devices.
DEBOUNCE_SECONDS = 60 * 15  # 15 minutes
assert DEBOUNCE_SECONDS > SCAN_INTERVAL  # Should not be less than SCAN_INTERVAL
