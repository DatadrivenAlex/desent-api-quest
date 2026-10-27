# Desent API Quest (Alexandru Cojocari)

FastAPI solution for [Desent API Quest](https://en.desent.io/coding-test-backend) (Back-end Developer).

## Endpoints
| Method | Path | Notes |
|--------|------|-------|
| GET | `/ping` | `{ "success": true }` |
| POST | `/echo` | Echo JSON body |
| POST | `/auth/token` | `{username,password}` → `{token}` (admin/password) |
| POST | `/books` | Create → 201 + `id` |
| GET | `/books` | Array; `?author=` filter; `?page=&limit=` |
| GET/PUT/DELETE | `/books/{id}` | 200 / 200 / 204; 404 if missing |
| POST | `/quest/enable-auth` | Turn on Bearer protection (before Level 5) |

Validation: missing `title`/`author` on create → 400.

## Auth progression
Desent Level 3 needs open `GET /books`; Level 5 needs 401 without token.  
Start with auth **off**. After Levels 1–4 pass:

```bash
curl -X POST "$BASE/quest/enable-auth"
```

Then run Levels 5–8.

## Run locally
```bash
cd api_quest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
# other terminal:
python scripts/simulate_quest.py http://127.0.0.1:8000
```

## Deploy (cloudflared tunnel)
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
cloudflared tunnel --url http://127.0.0.1:8000
# use the https://*.trycloudflare.com URL as Desent base URL
```

Keep the process running while Desent runs the live checks (Level 8 needs &lt;500ms).

## Candidate
Alexandru Cojocari — https://github.com/DatadrivenAlex  
Honesty: in-memory store, no Django/Firebase in this challenge (role mentions them; this quest is framework-agnostic).
