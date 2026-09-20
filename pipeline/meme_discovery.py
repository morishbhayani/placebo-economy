import sys
import re
import json
import duckdb
import requests
from collections import Counter
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"

if len(sys.argv) < 2:
    print("Usage: python3 meme_discovery.py <keyword>")
    sys.exit(1)

keyword = " ".join(sys.argv[1:]).lower()

print(f"\nSearching Calcifer for: {keyword!r}\n")

query = """
WITH latest AS (
    SELECT *
    FROM (
        SELECT
            id,
            author_id,
            body,
            created_at,
            retweet_count,
            like_count,
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
SELECT *
FROM latest
"""

df = duckdb.execute(query, [f"%{keyword}%"]).df()

print("Unique matching posts:", len(df))

if len(df) < 3:
    print("Not enough matching posts.")
    sys.exit()

def clean_text(text):
    text = re.sub(r'^RT @[^:]+:\s*', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

df["clean_text"] = df["body"].apply(clean_text)

counts = Counter(df["clean_text"])

# Keep posts that look more like health claims before asking the LLM.
# This prevents generic chatter such as "good night" from dominating.
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

candidate_texts = [
    text for text in counts.keys()
    if any(term in text.lower() for term in health_terms)
]

# Prefer repeated items, but do not throw away less common claims.
candidate_texts = sorted(
    candidate_texts,
    key=lambda x: counts[x],
    reverse=True
)[:500]

print("Health-like candidate posts:", len(candidate_texts))
print("\nFiltering for actual health claims with local LLM...\n")

health_claims = []

BATCH_SIZE = 20

for start in range(0, len(candidate_texts), BATCH_SIZE):
    batch = candidate_texts[start:start + BATCH_SIZE]

    numbered = "\n".join(
        f"{i}: {text}"
        for i, text in enumerate(batch)
    )

    prompt = f"""
You are filtering social-media posts for a public-health meme analysis system.

Topic searched by the user:
"{keyword}"

A HEALTH CLAIM is a statement that asserts, implies, questions, recommends,
or warns about a relationship between:

- a treatment, drug, supplement, food, behavior, exposure, disease, symptom,
  intervention, or health practice

AND

- a health outcome, symptom, risk, benefit, harm, diagnosis, prevention,
  recovery, or bodily effect.

Examples of HEALTH CLAIMS:
"Magnesium helps you sleep"
"Melatonin causes dependency"
"Blue light ruins sleep"
"Coffee after 5pm disrupts sleep"
"Eight hours of sleep is necessary for health"

NOT HEALTH CLAIMS:
"I can't sleep"
"Good night"
"Sleep well"
"I'm tired"
"Going to bed"

For each numbered post below, decide whether it contains a health claim.

Return JSON only:

{{
  "health_claim_indices": [0, 3, 7]
}}

POSTS:
{numbered}
"""

    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0
                }
            },
            timeout=180
        )

        r.raise_for_status()

        result = json.loads(r.json()["response"])
        indices = result.get("health_claim_indices", [])

        for idx in indices:
            if isinstance(idx, int) and 0 <= idx < len(batch):
                health_claims.append(batch[idx])

    except Exception as e:
        print("Batch error:", e)

print("Health-claim variants retained:", len(health_claims))

with open("data/processed/grounded_claims_source.json", "w") as f:
    json.dump(health_claims, f, indent=2)

print("Saved retained posts to grounded_claims_source.json")

print("\nRETAINED HEALTH CLAIMS\n")

for i, claim in enumerate(health_claims, 1):
    print(f"{i}. {claim}")

if len(health_claims) < 2:
    print("Not enough health claims found for clustering.")
    sys.exit()

# Group retained health claims into broader meme families using the local LLM.
#
# Why: health narratives may use very different wording, so strict embedding
# clustering can miss conceptually related claims.

items = []

for i, claim in enumerate(health_claims):
    items.append({
        "id": i,
        "text": claim,
        "observed_count": counts[claim]
    })

group_prompt = f"""
You are identifying distinct health meme families from social-media claims.

User topic:
"{keyword}"

A meme family must represent ONE SPECIFIC, evidence-checkable health claim.

GOOD family names:
- "Sleep deprivation increases cancer risk"
- "Multivitamins improve sleep quality"
- "Caffeine disrupts sleep"
- "Exercise improves sleep"
- "Chronotype affects alertness and sleep timing"

BAD family names:
- "Sleep is important"
- "Sleep affects health"
- "Healthy sleep"
- "Sleep and wellness"

STRICT RULES:

1. Every family must express a specific relationship:
   exposure/behavior/treatment → health outcome.

2. Do NOT create vague umbrella categories.

3. Two posts belong in the same family only if they make substantially
   the SAME underlying health claim.

4. Each post ID may appear in AT MOST ONE family.

5. Reject posts that:
   - merely mention sleep
   - describe personal circumstances without making a general health claim
   - are advertisements without a clear health claim
   - mention another illness as the reason someone cannot sleep
   - are jokes, greetings, or unrelated conversation

6. Do NOT invent mechanisms or outcomes that are not present in the posts.

7. Prefer narrower families over broad families.

8. A family with only one post is allowed. Mark it as "EMERGING".
   A family with two or more distinct posts is "REPEATED".

Return JSON only:

{{
  "families": [
    {{
      "name": "specific canonical health claim",
      "member_ids": [1, 4],
      "status": "REPEATED",
      "summary": "one precise sentence describing the shared health claim"
    }}
  ],
  "rejected_ids": [2, 5, 9]
}}

CLAIMS:
{json.dumps(items, ensure_ascii=False)}
"""

r = requests.post(
    OLLAMA_URL,
    json={
        "model": MODEL,
        "prompt": group_prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0
        }
    },
    timeout=240
)

r.raise_for_status()

try:
    family_result = json.loads(r.json()["response"])
except Exception as e:
    print("Could not parse meme-family grouping:", e)
    sys.exit()

families = family_result.get("families", [])

ranked = []

for family in families:

    valid_ids = [
        i for i in family.get("member_ids", [])
        if isinstance(i, int) and 0 <= i < len(items)
    ]

    if not valid_ids:
        continue

    prevalence = sum(
        items[i]["observed_count"]
        for i in valid_ids
    )

    member_texts = [
        items[i]["text"]
        for i in valid_ids
    ]

    ranked.append({
        "name": family.get("name", "Unnamed narrative"),
        "summary": family.get("summary", ""),
        "prevalence": prevalence,
        "variants": len(member_texts),
        "texts": member_texts
    })

ranked.sort(
    key=lambda x: (
        x["prevalence"],
        x["variants"]
    ),
    reverse=True
)

print("\nTOP HEALTH MEME FAMILIES\n")

for i, family in enumerate(ranked[:3], 1):

    print("=" * 80)
    print(f"MEME {i}")
    print("Narrative:", family["name"])
    print("Observed posts:", family["prevalence"])
    print("Distinct variants:", family["variants"])
    print("Summary:", family["summary"])

    print("\nExample posts:")

    for t in family["texts"][:5]:
        print(" -", t[:400])

    print()
if not ranked:
    print("No usable health meme families found.")
