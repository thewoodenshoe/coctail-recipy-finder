# Network Troubleshooting

## Current Public Access Shape

The Cocktail Recipe Finder app runs directly on the Ubuntu server:

```text
0.0.0.0:8000
```

The Ubuntu server LAN IP observed during setup:

```text
192.168.86.250
```

The WAN/public IP observed from the Ubuntu server:

```text
170.52.149.139
```

Expected public URL when router forwarding works:

```text
http://170.52.149.139:8000/
```

## Required Direct-Port Setup

All three layers must be true:

1. App is listening on all interfaces:

```bash
ss -ltnp | grep ':8000'
```

Expected:

```text
0.0.0.0:8000 ... uvicorn
```

2. Ubuntu firewall allows TCP `8000`:

```bash
sudo ufw status numbered
```

Expected:

```text
8000/tcp ALLOW IN Anywhere
```

3. Google Home/router forwards:

```text
External TCP 8000 -> 192.168.86.250 TCP 8000
```

## Test Order

Run these in order:

```bash
curl -fsS http://127.0.0.1:8000/
curl -fsS http://192.168.86.250:8000/
curl -fsS http://170.52.149.139:8000/
```

Interpretation:

- `127.0.0.1:8000` works: the app process is healthy.
- `192.168.86.250:8000` works: LAN routing and Ubuntu firewall are healthy.
- `170.52.149.139:8000` fails from inside the LAN: this may be normal if the router does not support hairpin NAT. Test from a phone on cellular or another external network.
- `170.52.149.139:8000` fails from a true external network: the remaining likely causes are router forwarding not actually applied, forwarding to the wrong LAN device, upstream ISP filtering, double NAT, or a changed LAN IP.

## CHS Finds / CHS Spots Findings

Do not copy CHS Finds networking assumptions blindly.

CHS Finds / CHS Spots is not exposed as a plain direct-IP app:

- nginx owns ports `80`, `443`, and `8080` on the Ubuntu host.
- CHS Spots main app uses port `3000`.
- Umami uses `3001`.
- Admin uses `3456`.
- The CHS firewall setup is Cloudflare-oriented.
- `scripts/ops/setup-cloudflare-firewall.sh` allows Cloudflare IP ranges for `80/443` and deletes broad public rules for `80`, `443`, and `8080`.

That means `8080` is not a safe reusable port for this project. It is already owned by nginx and CHS-related configuration.

For this project's direct-port MVP, use `8000` unless a later architectural decision moves the app behind nginx or Cloudflare.

## If Direct Port Still Fails

If the app works on LAN but not from a real external network after the router rule is confirmed, do not randomly change nginx or CHS settings.

Correct next options:

1. Re-check Google Home forwarding points to the current Ubuntu LAN IP, `192.168.86.250`.
2. Confirm the WAN IP shown by Google Home matches `170.52.149.139`.
3. Test from cellular, not from the same Wi-Fi.
4. If direct forwarding remains unreliable, use a Cloudflare Tunnel or a proper nginx/Cloudflare/domain setup for this project.

The CHS project already chose Cloudflare Tunnel specifically to avoid direct NAT/port-forward fragility.
