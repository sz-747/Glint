import json
import re
import sqlite3
from pathlib import Path


def normalize_text(text):
    """Normalize text for deterministic quote/chunk deduplication."""
    if text is None:
        return ""

    lowered = str(text).lower()
    no_punctuation = re.sub(r"[^\w\s']", " ", lowered)
    collapsed = re.sub(r"\s+", " ", no_punctuation).strip()
    return collapsed


def load_seed_rows(seed_path):
    with seed_path.open("r", encoding="utf-8") as seed_file:
        data = json.load(seed_file)
    if not isinstance(data, list):
        raise ValueError("Seed file must contain a top-level JSON array.")
    return data


def main():
    repo_root = Path(__file__).resolve().parents[1]
    seed_path = repo_root / "data" / "default_quotes.json"
    db_path = repo_root / "instance" / "glint.db"

    if not seed_path.exists():
        raise FileNotFoundError(f"Missing seed file: {seed_path}")
    if not db_path.exists():
        raise FileNotFoundError(f"Missing SQLite database: {db_path}")

    seed_rows = load_seed_rows(seed_path)

    quotes_created = 0
    quotes_updated = 0
    chunks_inserted = 0
    skipped_invalid = 0

    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.cursor()

        for row in seed_rows:
            if not isinstance(row, dict):
                skipped_invalid += 1
                continue

            quote_text = str(row.get("quote_text", "")).strip()
            source_label_raw = row.get("source_label")
            source_label = str(source_label_raw).strip() if source_label_raw is not None else None
            if source_label == "":
                source_label = None

            raw_chunks = row.get("analysis_chunks", [])
            if not isinstance(raw_chunks, list):
                skipped_invalid += 1
                continue

            normalized_quote = normalize_text(quote_text)
            if not normalized_quote:
                skipped_invalid += 1
                continue

            normalized_chunks = []
            for chunk in raw_chunks:
                chunk_text = str(chunk).strip()
                chunk_normalized = normalize_text(chunk_text)
                if chunk_normalized:
                    normalized_chunks.append((chunk_text, chunk_normalized))

            if not normalized_chunks:
                skipped_invalid += 1
                continue

            existing_quote = cursor.execute(
                "SELECT id, source_label FROM quote_entry WHERE quote_normalized = ?",
                (normalized_quote,),
            ).fetchone()

            if existing_quote is None:
                cursor.execute(
                    """
                    INSERT INTO quote_entry (quote_text, quote_normalized, source_label, created_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (quote_text, normalized_quote, source_label),
                )
                quote_id = cursor.lastrowid
                quotes_created += 1
            else:
                quote_id = existing_quote[0]
                existing_source = existing_quote[1]
                if source_label and not existing_source:
                    cursor.execute(
                        "UPDATE quote_entry SET source_label = ? WHERE id = ?",
                        (source_label, quote_id),
                    )
                    quotes_updated += 1

            existing_chunks = cursor.execute(
                "SELECT chunk_text FROM analysis_chunk WHERE quote_id = ?",
                (quote_id,),
            ).fetchall()
            existing_chunk_norm = {normalize_text(chunk_text) for (chunk_text,) in existing_chunks}

            for chunk_text, chunk_normalized in normalized_chunks:
                if chunk_normalized in existing_chunk_norm:
                    continue
                cursor.execute(
                    """
                    INSERT INTO analysis_chunk (quote_id, chunk_text, quality_score, created_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (quote_id, chunk_text, 1.0),
                )
                existing_chunk_norm.add(chunk_normalized)
                chunks_inserted += 1

        connection.commit()
    finally:
        connection.close()

    print(f"quotes_created={quotes_created}")
    print(f"quotes_updated={quotes_updated}")
    print(f"chunks_inserted={chunks_inserted}")
    print(f"skipped_invalid={skipped_invalid}")


if __name__ == "__main__":
    main()
