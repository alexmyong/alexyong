#!/usr/bin/env python3
"""Check a candidate password against the hashes in the env file.

Usage: sudo python3 check_password.py [/etc/anki-syncserver.env]
The candidate is read without echo (or from stdin when not a terminal).
Prints only MATCH / no match per user, never the password or hashes.
"""
import base64, getpass, hashlib, hmac, re, sys

ENV = sys.argv[1] if len(sys.argv) > 1 else "/etc/anki-syncserver.env"
LINE = re.compile(r"SYNC_USER\d+=([^:]+):\$pbkdf2-sha256\$i=(\d+),l=(\d+)\$([^$]+)\$(\S+)")


def unb64(s: str) -> bytes:
    return base64.b64decode(s + "=" * (-len(s) % 4))


candidate = getpass.getpass("Password to check: ") if sys.stdin.isatty() else sys.stdin.readline().rstrip("\n")

for line in open(ENV):
    m = LINE.match(line)
    if not m:
        continue
    user, iters, length, salt, expected = m.groups()
    dk = hashlib.pbkdf2_hmac("sha256", candidate.encode(), unb64(salt), int(iters), int(length))
    print(f"{user}: {'MATCH' if hmac.compare_digest(dk, unb64(expected)) else 'no match'}")
