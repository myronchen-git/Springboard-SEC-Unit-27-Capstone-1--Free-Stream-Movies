import json

from src.exceptions.base_exceptions import FreeStreamMoviesServerError
from src.util.logger import create_logger

# ==================================================

logger = create_logger(__name__, 'src/logs/seed.log')

# --------------------------------------------------


def read_services_blacklist() -> set:
    """
    Reads services_blacklist.txt and puts the streaming service names into a Set.

    :return: A Set containing blacklisted streaming services.
    :raise FreeStreamMoviesServerError: If there is an issue with opening the blacklist file.
    """

    location = "src/services_blacklist.txt"

    blacklist = set()

    try:
        with open(location, "r") as f:
            for line in f:
                blacklist.add(line.strip().lower())
        return blacklist

    except OSError as e:
        logger.error('Unable to open blacklist file.'
                     f'Error is\n{str(e)}')
        raise FreeStreamMoviesServerError(str(e))


def read_json_file_helper(file_location: str) -> dict:
    """
    Opens a JSON file and parses the contents.

    :param file_location: The location of the file, relative to root.
    :return: A dictionary.
    """

    try:
        with open(file_location) as f:
            contents = json.loads(f.read())
            logger.info("JSON file successfully read and parsed.")
            logger.debug(f'Contents are {contents}.')
            return contents

    except OSError as e:
        logger.warning('JSON file does not exist.  Returning empty dict.\n'
                       f'Error is\n{str(e)}')
        return {}


def write_json_file_helper(file_location: str, contents: dict) -> None:
    """
    Writes the dictionary of contents to a file.  Overwrites existing file.

    :param file_location: The location of the file, relative to root.
    :param contents: A dictionary.
    :raise FreeStreamMoviesServerError: If there is an issue with opening or writing to the file.
    """

    logger.debug(f'Writing contents to file. Contents are {contents}.')

    try:
        with open(file_location, 'w') as f:
            f.write(json.dumps(contents, indent=4, sort_keys=True))
        logger.info("Contents written to file.")

    except OSError as e:
        logger.error('Unable to write to JSON file.'
                     f'Error is\n{str(e)}')
        raise FreeStreamMoviesServerError(str(e))
