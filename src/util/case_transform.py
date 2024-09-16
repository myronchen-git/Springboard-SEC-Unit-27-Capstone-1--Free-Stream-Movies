import re

# ==================================================


class CamelToSnake():
    """https://stackoverflow.com/a/1176023"""

    pattern = None

    @classmethod
    def transform(cls, str):
        cls.pattern = cls.pattern or re.compile(r'(?<!^)(?=[A-Z])')
        name = cls.pattern.sub('_', str).lower()
        return name
