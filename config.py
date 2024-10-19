import logging

# Configuration settings

# LOGGING_LEVEL: Specifies the logging level for the application.
# Possible values include 'DEBUG', 'INFO', 'WARNING', 'ERROR', and 'CRITICAL'.
# See https://docs.python.org/3/library/logging.html#logging-levels for more information
LOGGING_LEVEL = logging.INFO

# LOGGING_FORMATTER: The formatter the applicaiton will use for logging.
# See https://docs.python.org/3/library/logging.html#logrecord-attributes for more information
LOGGING_FORMATTER = logging.Formatter(
    "%(asctime)s - %(name)s.%(funcName)s - %(levelname)s - %(message)s"
)

# DATABASE: The file path to the SQLite database used for storing user information.
DATABASE = "users.db"

# FORCE_LOGOUT_HOUR: The hour (in 24-hour format) at which all users should be forcefully logged out.
# This ensures that users who haven't been logged out are automatically logged out daily.
# Value is set in 24-hour format; e.g., 22 means 10:00 PM.
FORCE_LOGOUT_HOUR = 22  # TODO: Artifact from old system?

# SUBNETS: A list of subnet ranges to be scanned by Nmap to detect active devices.
# Each subnet is specified in a format recognized by Nmap. For example, "192.168.0.*" means
# all devices in the "192.168.0.x" IP range will be scanned.
SUBNETS = ["192.168.0.*"]

# SCAN_INTERVAL: The interval, in seconds, between each scan of the network.
# This value controls how frequently the network is scanned for user devices.
SCAN_INTERVAL = 5

# SCAN_TIMEOUT: The maximum time, in seconds, to wait for the network scan to complete.
# If the scan exceeds this time, it will be considered a timeout.
SCAN_TIMEOUT = 120

# DEBOUNCE_SECONDS: The debounce time threshold, in seconds, to determine user inactivity.
# If a user is not detected on the network within this time frame, they will be logged out.
# It is recommended to be five times the scan interval.
DEBOUNCE_SECONDS = SCAN_INTERVAL * 5
