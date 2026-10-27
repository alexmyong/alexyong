#!/usr/bin/env python3
"""Log in to the sync server the way Anki does, using a throwaway collection.

Run with the server's venv on the Pi:
  ~/syncserver/bin/python test_login.py <username> [endpoint]
Default endpoint: http://127.0.0.1:41641/
"""
import getpass, os, sys, tempfile

from anki.collection import Collection

if len(sys.argv) < 2:
    sys.exit(__doc__)
user = sys.argv[1]
endpoint = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:41641/"
password = getpass.getpass("Password: ") if sys.stdin.isatty() else sys.stdin.readline().rstrip("\n")

with tempfile.TemporaryDirectory() as d:
    col = Collection(os.path.join(d, "test.anki2"))
    try:
        col.sync_login(user, password, endpoint)
        print(f"{user}: login OK")
    except Exception as e:
        print(f"{user}: rejected ({type(e).__name__})")
        sys.exit(1)
    finally:
        col.close()
