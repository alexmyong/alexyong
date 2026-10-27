#!/usr/bin/env python3
"""Print a SYNC_USERn line with a PHC pbkdf2-sha256 password hash.

Usage: python3 hash_password.py <n> <username>
The password is read without echo (or from stdin when not a terminal).
Paste the output line into /etc/anki-syncserver.env.
"""
import base64, getpass, hashlib, os, sys

ITERATIONS = 600_000


def b64(b: bytes) -> str:
    return base64.b64encode(b).decode().rstrip("=")


def phc(password: str, iterations: int = ITERATIONS) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations, 32)
    return f"$pbkdf2-sha256$i={iterations},l=32${b64(salt)}${b64(dk)}"


def read_password() -> str:
    if not sys.stdin.isatty():
        return sys.stdin.readline().rstrip("\n")
    pw = getpass.getpass("Password: ")
    if pw != getpass.getpass("Again: "):
        sys.exit("Passwords don't match.")
    return pw


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    n, user = sys.argv[1], sys.argv[2]
    password = read_password()
    if not password:
        sys.exit("Empty password.")
    print(f"SYNC_USER{n}={user}:{phc(password)}")
