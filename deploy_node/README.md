# Node deploy mirror

Zero-dependency Node `http` server mirroring `app/main.py` for hosts without Python.
Used to expose a public tunnel from the user's Windows workstation when the box blocks cloudflared.

```bash
node server.js
# PORT=8000 AUTH_REQUIRED=0
```
