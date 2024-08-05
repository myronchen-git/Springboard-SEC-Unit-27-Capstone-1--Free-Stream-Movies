def read_services_blacklist() -> set:
    """
    Reads services_blacklist.txt and puts the streaming service names into a Set.

    Returns a Set containing blacklisted streaming services.
    """

    location = "src/services_blacklist.txt"

    blacklist = set()

    with open(location, "r") as f:
        for line in f:
            blacklist.add(line.strip().lower())

    return blacklist
