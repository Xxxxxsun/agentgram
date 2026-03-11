import secrets
import bcrypt


def generate_api_key() -> str:
    return "sk_ag_" + secrets.token_urlsafe(32)


def hash_key(raw_key: str) -> str:
    return bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()


def verify_key(raw_key: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw_key.encode(), hashed.encode())


def get_key_prefix(raw_key: str) -> str:
    return raw_key[:14]
