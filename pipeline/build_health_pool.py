import re
import json
import duckdb
import sys

keyword = " ".join(sys.argv[1:]).lower() if len(sys.argv) > 1 else "sleep"

query = """
WITH latest AS (
    SELECT *
    FROM (
        SELECT
            id,
            author_id,
            body,
            created_at,
            like_count,
            reply_count,
            retweet_count,
            quote_count,
            views_count,
            version,
            ROW_NUMBER() OVER (
                PARTITION BY id
                ORDER BY version DESC
            ) AS rn
        FROM read_parquet('tweets-*.parquet', union_by_name=true)
        WHERE lang = 'en'
          AND lower(body) LIKE ?
    )
    WHERE rn = 1
)
SELECT
    id,
    author_id,
    body,
    created_at,
    like_count,
    reply_count,
    retweet_count,
    quote_count,
    views_count
FROM latest
"""

df = duckdb.execute(query, [f"%{keyword}%"]).df()

health_terms = [
    "cause", "causes", "caused",
    "risk", "risks",
    "increase", "increases", "increased",
    "reduce", "reduces", "reduced",
    "improve", "improves", "improved",
    "help", "helps",
    "harm", "harmful",
    "benefit", "benefits",
    "study", "research",
    "linked", "associated",
    "treat", "treatment",
    "prevent", "prevents",
    "side effect",
    "symptom", "symptoms",
    "doctor", "medication", "drug",
    "supplement",
    "mortality",
    "depression", "anxiety",
    "migraine", "fatigue",
    "insomnia",
    "health"
]

def clean(text):
    text = re.sub(r'^RT @[^:]+:\s*', '', str(text))
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

df["clean_text"] = df["body"].apply(clean)

pool = []

for _, row in df.iterrows():

    text = row["clean_text"]

    if any(term in text.lower() for term in health_terms):

        pool.append({
            "id": str(row["id"]),
            "author_id": str(row["author_id"]),
            "created_at": str(row["created_at"]),
            "text": text,
            "like_count": int(row["like_count"] or 0),
            "reply_count": int(row["reply_count"] or 0),
            "retweet_count": int(row["retweet_count"] or 0),
            "quote_count": int(row["quote_count"] or 0),
            "views_count": int(row["views_count"] or 0)
        })

with open("data/processed/health_candidate_pool.json", "w") as f:
    json.dump(pool, f, indent=2)

print("Keyword:", keyword)
print("Total unique matching posts:", len(df))
print("Health-like searchable posts:", len(pool))
print("Saved to health_candidate_pool.json")
