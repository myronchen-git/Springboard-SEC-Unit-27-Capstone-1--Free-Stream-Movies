import json

from src.util.logger import create_logger

# ==================================================

logger = create_logger(__name__, 'src/logs/seed.log')

cursor_file_location = 'src/seed/streaming_availability_cursors.json'

# --------------------------------------------------


def read_services_blacklist() -> set:
    """
    Reads services_blacklist.txt and puts the streaming service names into a Set.

    :return: A Set containing blacklisted streaming services.
    """

    location = "src/services_blacklist.txt"

    blacklist = set()

    with open(location, "r") as f:
        for line in f:
            blacklist.add(line.strip().lower())

    return blacklist


def retrieve_cursor_file_helper() -> dict:
    """
    Opens the cursor file and parses the JSON data for next cursors.

    :return: A dictionary containing country codes, for each country code to contain service IDs,
        and for each service ID to contain the next cursor to use.  This won't contain countries or services
        that didn't have a next cursor.  This will be an empty dict if the file does not exist.
        ({country: {service_id: cursor}})
    """

    try:
        with open(cursor_file_location) as f:
            cursors = json.loads(f.read())
            logger.info("Cursors file successfully read and parsed.")
            logger.debug(f'cursors = {cursors}.')
            return cursors

    except OSError:
        logger.warn("Cursors file does not exist.  Returning empty dict.")
        return {}


def write_cursor_file_helper(cursors: dict) -> None:
    """
    Writes the dictionary of cursors to the cursor file.

    :param cursors: A dictionary containing country codes, for each country code to contain service IDs,
        and for each service ID to contain the next cursor to use.  ({country: {service_id: cursor}})
    """

    logger.debug(f'Writing cursors to file. cursors = {cursors}.')

    with open(cursor_file_location, 'w') as f:
        f.write(json.dumps(cursors, indent=4, sort_keys=True))

    logger.info("Cursors written to file.")
