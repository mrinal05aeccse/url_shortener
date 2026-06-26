import random
import string


ALPHABET = string.ascii_letters + string.digits


def generate_alias(length: int = 6) -> str:
    return ''.join(random.choices(ALPHABET, k=length))
