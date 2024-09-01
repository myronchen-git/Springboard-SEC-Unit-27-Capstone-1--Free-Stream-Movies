import logging

# ==================================================


def create_logger(module_name: str, filepath: str) -> logging.Logger:
    """
    Creates a logger for the specified module, which will output logs at the specified filepath.
    Filepath is relative to the root directory of this project.

    :param module_name: Name of the module that this logger is for.
    :param filepath: Path and file name to store the logs in.
    :return: A Logger instance from Python's logging module.
    """

    logger = logging.getLogger(module_name)
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)s, %(filename)s - line %(lineno)d, %(funcName)s: %(message)s')

    file_handler = logging.FileHandler(filepath, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger
