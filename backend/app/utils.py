import secrets
import string

ALIAS_LENGTH = 6
ALIAS_ALPHABET = string.ascii_letters + string.digits


def generate_alias(length: int = ALIAS_LENGTH) -> str:
    """
    Generate a short random alias suitable for a short URL.
    """
    return "".join(secrets.choice(ALIAS_ALPHABET) for _ in range(length))