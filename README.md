# URL Shortener (Flask + SQLite)

## Run
```bash
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## API
| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/shorten` | Body `{"url": "https://..."}` → `{code, original_url, short_url}` |
| GET | `/<code>` | 302 redirect to the original URL (counts a click) |
| GET | `/api/stats/<code>` | Original URL, click count, created time |

## Test with curl
```bash
curl -X POST http://127.0.0.1:5000/api/shorten \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.wikipedia.org"}'
curl -i http://127.0.0.1:5000/<code>
```

## Notes
- Codes are 6 random base62 characters (~56 billion combinations), checked for uniqueness before saving.
- Data lives in `urls.db` (SQLite), created automatically. Override the path with the `DB_PATH` env var.
