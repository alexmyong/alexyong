# Custom Anki Server

A self-hosted [Anki sync server](https://docs.ankiweb.net/manual/sync-server) on a Raspberry Pi 5, reached from anywhere over [Tailscale](https://tailscale.com). Replaces AnkiWeb for my own collections.

```
Mac / phone (Anki 26.x) ──Tailscale (WireGuard)──▶ Raspberry Pi 5
                                                    └─ anki-syncserver.service  :41641
                                                       └─ ~/.syncserver/<user>/
```

## What's in this folder

| Path | What it is |
|---|---|
| `systemd/anki-syncserver.service` | systemd unit: starts at boot, restarts on failure, sandboxed to `~/.syncserver` |
| `systemd/anki-syncserver.env.example` | Server settings template (users, hashed passwords, port). The real one lives at `/etc/anki-syncserver.env`, root-only |
| `scripts/hash_password.py` | Makes a `SYNC_USERn=user:<pbkdf2 hash>` line from a password typed without echo |
| `scripts/check_password.py` | Says whether a password matches a user's stored hash (prints only MATCH / no match) |
| `scripts/test_login.py` | Logs in to the server exactly like Anki does, using a throwaway collection |
| `desktop/AnkiSyncLogs.desktop` | Pi desktop launcher that opens a live log terminal |
| `ssh/00-hardening.conf` | sshd drop-in: key-only logins, no root |
| `ssh/ssh_config.example` | Mac-side `Host rpi` entry |

No real passwords, hashes or keys are in this repo.

## Setup

### 1. SSH into the Pi over Tailscale

Both machines are on the same tailnet; the Pi is `rpi` via MagicDNS.

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_rpi
ssh-copy-id -i ~/.ssh/id_rpi.pub rpi
```

Add `ssh/ssh_config.example` to `~/.ssh/config`, then `ssh rpi`. Once key login works, install `ssh/00-hardening.conf` to `/etc/ssh/sshd_config.d/`, run `sudo sshd -t`, then `sudo systemctl reload ssh`.

### 2. Install / update the sync server

The server runs from a Python venv at `~/syncserver` on the Pi:

```bash
python3 -m venv ~/syncserver
~/syncserver/bin/pip install --upgrade anki
```

Keep the server version in step with the Anki clients (currently 26.9.3 on both). Newer clients can need a newer server.

### 3. Users and hashed passwords

For each user, on the Pi:

```bash
python3 scripts/hash_password.py 1 you@example.com
```

Put the printed lines plus the rest of `anki-syncserver.env.example` into `/etc/anki-syncserver.env`:

```bash
sudo install -o root -g root -m 600 anki-syncserver.env /etc/anki-syncserver.env
```

`PASSWORDS_HASHED=1` tells the server the passwords are hashes. Hashes are PHC-format `pbkdf2-sha256` (600,000 iterations); the server also accepts `pbkdf2-sha512`. Each user's data goes in `~/.syncserver/<username>/`, so renaming a user means renaming that folder too. The hash doesn't depend on the username, so a rename doesn't need the password.

### 4. Run it as a service

```bash
sudo cp systemd/anki-syncserver.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now anki-syncserver
```

Check that a real login works:

```bash
~/syncserver/bin/python scripts/test_login.py you@example.com
```

### 5. Point Anki at it

In Anki, go to **Settings → Syncing → Self-hosted sync server** and enter `http://<pi-tailscale-ip>:41641/` (or `http://rpi:41641/`). Keep the trailing slash. **Quit Anki fully (Cmd+Q)** and reopen; the setting is only read at startup. Click **Sync**, sign in, and on the first sync of a fresh server choose **Upload**.

### 6. Live logs on the Pi desktop

Copy `desktop/AnkiSyncLogs.desktop` to `~/Desktop/` and `chmod +x` it. It needs no sudo because `alex` is in the `adm` group.

## Day-to-day

```bash
sudo systemctl status anki-syncserver
```

```bash
sudo journalctl -u anki-syncserver -f
```

```bash
sudo systemctl restart anki-syncserver
```

Restart after any edit to `/etc/anki-syncserver.env`.

## Gotchas I hit

**AnkiHub hijacks the sign-in box.** With the AnkiHub add-on enabled, Anki's "Sign into AnkiWeb" dialog (the one offering a "magic code") is AnkiHub's. It always posts credentials to AnkiWeb and ignores the self-hosted server setting, so you get "Inserted e-mail and/or password are incorrect" and nothing ever reaches the Pi. Fix: **Tools → Add-ons → AnkiHub → Toggle Enabled**, restart Anki, sign in, then re-enable it if you use it. Normal syncing afterwards still goes to the Pi; only the sign-in dialog is affected.

**Check the server log first.** If `journalctl -u anki-syncserver` shows no `/sync/hostKey` request, the client never reached the server and the password isn't the problem.

**Wi-Fi client isolation.** The Pi's Wi-Fi couldn't reach any other device on the LAN (not even the router), only the internet. So Tailscale couldn't connect directly and relayed everything through its London DERP server, at about 1.25 MB/s. That's fine for reviews, but the first media upload (hundreds of thousands of files) takes hours. Fixes: plug the Pi into the router with Ethernet, or turn off AP/client isolation. `tailscale ping rpi` should then say `via <lan-ip>` instead of `via DERP`.

**`pgrep -f anki.syncserver` matches itself.** It matches any shell command line that contains that text, including the one doing the killing. Use `pgrep -f "[a]nki.syncserver"` or, better, just `systemctl`.

## Security notes

- The server speaks plain HTTP; Tailscale's WireGuard tunnel provides the encryption. Don't expose port 41641 to the internet.
- Passwords are stored only as salted pbkdf2 hashes in a root-only file. The old start script with plain-text passwords (and its copies in backups and shell history) was deleted.
- SSH is key-only with root login disabled.
- Not done yet: a host firewall limiting SSH and the sync port to `tailscale0`. While the Wi-Fi isolation above is in place it happens to block LAN access, but that's not something to rely on.
- The Pi was also cleaned up: Apache, PHP, phpMyAdmin, MariaDB, Samba (which was sharing `/`), CUPS removed; Bluetooth and Avahi disabled.
