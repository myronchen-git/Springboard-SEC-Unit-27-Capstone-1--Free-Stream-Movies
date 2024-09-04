from src.util.file_handling import read_services_blacklist

# ==================================================

BLACKLISTED_SERVICES = read_services_blacklist()
STREAMING_AVAILABILITY_API_REQUEST_RATE_LIMIT_PER_SECOND = 10
STREAMING_AVAILABILITY_API_REQUEST_RATE_LIMIT_PER_DAY = 100
