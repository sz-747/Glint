# HSC Software Engineering AT2 - Glint

## App Description

Glint is a writing tool with a distraction-free editor and a local "Ghost Writer" helper.

Phase 2 now uses a **quote-to-analysis retrieval engine** (pivot from n-gram generation).  
When a user types a known quote (exact, in-progress prefix, or fuzzy typo match), the app retrieves a mapped analysis sentence from SQLite and shows it as ghost text in the dashboard editor.

Current Ghost Writer behavior:
- Live suggestion API: `POST /api/suggest-analysis`
- In-editor ghost suggestion rendering with debounce
- `Tab` to accept suggestion, `Esc` to dismiss
- Suggestion interaction logging via `POST /api/log-suggestion`

This keeps suggestions deterministic, fast, and private without external AI APIs.

## Local Setup

Use the project virtual environment so all Flask dependencies are available.

```powershell
# from repo root
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If you prefer `py`, install dependencies with:

```powershell
py -m pip install -r requirements.txt
```

Load starter quote-analysis rows into SQLite once:

```powershell
.\venv\Scripts\python.exe scripts\backfill_quotes.py
```

Then run the app:

```powershell
python app.py
```

```powershell
py app.py
```

Notes:
- App startup now creates tables but does not auto-seed quote data.
- If `quote_entry` is empty, suggestion APIs return no analysis until quotes are backfilled or added via admin endpoints.
