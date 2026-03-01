# HSC Software Engineering AT2 - Glint

## App Description

Glint is a tool for optimising the current writing workflow. The aim is to reduce friction between changing different tabs and breaking the flow state. 
Users are able to create files and insert quotes and basic formatting.
Admins are able to view all files, create/delete new users, see when the docs are created.
Analysis is pre-set in the database for each quote. There will be a suggestive analysis for each quote when the user inserts in a quote.

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
py app.py
```

Notes:
- App startup now creates tables but does not auto-seed quote data.
- If `quote_entry` is empty, suggestion APIs return no analysis until quotes are backfilled or added via admin endpoints.
