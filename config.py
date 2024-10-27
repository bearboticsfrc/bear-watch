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

# SUBNETS: A list of subnet ranges to be scanned to detect active devices.
# Each subnet is specified in CIDR format. For example, "192.168.0.0/24" means
# all devices in the "192.168.0.x" IP range will be scanned.
SUBNETS = ("192.168.0.0/24",)

# SCAN_INTERVAL: The interval, in seconds, between each scan of the network.
# This value controls how frequently the network is scanned for user devices.
SCAN_INTERVAL = 60

# HOST_RESPONSE_TIMEOUT: The maximum time, in seconds, to wait for a host to respond to our ARP packet.
# If the ping exceeds this time, it will be considered a timeout.
# It is highly recommended to leave this as the default!
HOST_RESPONSE_TIMEOUT = 5

# DEBOUNCE_SECONDS: The debounce time threshold, in seconds, to determine user inactivity.
# If a user is not detected on the network within this time frame, they will be logged out.
# It is recommended to be quite high, as Nmap will often not see some devices.
DEBOUNCE_SECONDS = 60 * 15  # 15 minutes
assert DEBOUNCE_SECONDS > SCAN_INTERVAL  # Should not be less than SCAN_INTERVAL
