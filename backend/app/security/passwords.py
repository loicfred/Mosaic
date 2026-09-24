"""Password hashing with Argon2id (argon2-cffi defaults to the Argon2id variant)."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# OWASP-recommended ballpark: 64 MiB memory, 3 iterations, parallelism 2.
_hasher = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=2, hash_len=32, salt_len=16)

# Used to spend the same time when an email does not exist (prevents user enumeration by timing).
_DUMMY_HASH = _hasher.hash("not-a-real-password-used-for-timing-only")

MIN_PASSWORD_LENGTH = 12


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def password_problems(password: str, email: str | None = None) -> list[str]:
    problems = []
    if len(password) < MIN_PASSWORD_LENGTH:
        problems.append(f"Use at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password) > 128:
        problems.append("Use at most 128 characters.")
    if email and email.split("@")[0].lower() in password.lower():
        problems.append("Do not include your email name in the password.")
    if len(set(password)) < 5:
        problems.append("Use a less repetitive password.")
    return problems
