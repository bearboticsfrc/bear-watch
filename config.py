LOGGING_LEVEL = "error" # Logging level

DATABASE = "users.db" # file which should be used as the sqlite3 database.

FORCE_LOGOUT_HOUR = 22 # At what hour should we force logout all users (24-hour).

SUBNETS = ["192.168.4.*", "192.168.5.*", "192.168.6.*", "192.168.7.*"] # A list of networks in a notation recognized by Nmap to scan for active devices.

SCAN_INTERVAL = 300 # How often to scan the network for users.

DEBOUNCE_SECONDS = SCAN_INTERVAL * 12 # Time threshold to debounce network absence before logging out users.