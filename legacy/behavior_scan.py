import duckdb
import re

rows = duckdb.sql("""
SELECT
    created_at,
    author_id,
    body
FROM read_parquet('tweets-000000.parquet')
WHERE lang = 'en'
  AND (
        lower(body) LIKE '%covid vaccine%'
        OR lower(body) LIKE '%mrna vaccine%'
        OR lower(body) LIKE '%pfizer%'
      )
  AND (
        lower(body) LIKE '%cancer%'
        OR lower(body) LIKE '%turbo cancer%'
      )
ORDER BY created_at
""").fetchall()

patterns = {
    "AVOID": [
        r"\bavoid\b",
        r"\bdon'?t get\b",
        r"\bdo not get\b",
        r"\bstay away\b"
    ],
    "REFUSE": [
        r"\brefus",
        r"\bwon'?t get\b",
        r"\bwill not get\b",
        r"\bnever get\b",
        r"\bnot taking\b"
    ],
    "STOP": [
        r"\bstop taking\b",
        r"\bno more shots\b",
        r"\bno more vaccines\b"
    ],
    "RECOMMEND_AGAINST": [
        r"\bdon'?t take\b",
        r"\bdo not take\b",
        r"\bshouldn'?t get\b",
        r"\bshould not get\b"
    ]
}

matches = []

for created_at, author_id, body in rows:
    text = body.lower()

    labels = []

    for label, expressions in patterns.items():
        if any(re.search(expr, text) for expr in expressions):
            labels.append(label)

    if labels:
        matches.append((created_at, author_id, labels, body))

print("\nBEHAVIORAL INTENTION SCAN\n")
print("Relevant vaccine+cancer posts:", len(rows))
print("Posts with explicit behavior signals:", len(matches))

rate = (len(matches) / len(rows) * 100) if rows else 0

print(f"Behavioral Intention Rate: {rate:.2f}%")

for i, row in enumerate(matches, 1):
    print(f"\n--- MATCH {i} ---")
    print("Date:", row[0])
    print("Author:", row[1])
    print("Labels:", ", ".join(row[2]))
    print(row[3])
