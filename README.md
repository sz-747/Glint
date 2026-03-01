# HSC Software Engineering AT2 - Glint

## App Description

Glint is a tool for optimising the current writing workflow. The aim is to reduce friction between changing different tabs and breaking the flow state. 
Users are able to create files and insert quotes and basic formatting.
Admins are able to view all files, create/delete new users, see when the docs are created.
Analysis is pre-set in the database for each quote. There will be a suggestive analysis for each quote when the user inserts in a quote.

## Local Setup

install dependencies with: py -m pip install -r requirements.txt

Load starter quote-analysis rows into SQLite once: .\venv\Scripts\python.exe scripts\backfill_quotes.py

Notes:
- App startup now creates tables but does not auto-seed quote data.
- If there are no admins then use the flask create-admin command to create the first 
