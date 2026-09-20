import json
import re
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"

with open("data/processed/grounded_claims_source.json", "r") as f:
    source_posts = json.load(f)

def normalize(s):
    return re.sub(r"\s+", " ", str(s)).strip()

def bad_quote(q):
    q = normalize(q)

    if len(q) < 3:
        return True

    # Reject obvious truncation
    if q.endswith("…") or q.endswith("..."):
        return True

    return False


grounded = []

for i, post in enumerate(source_posts, 1):

    prompt = f"""
You are extracting a specific, evidence-checkable health claim.

POST:
{post}

A VALID health claim must contain:

EXPOSURE / TREATMENT / BEHAVIOR
→
SPECIFIC HEALTH OUTCOME / RISK / BENEFIT / HARM

VALID examples:
"Caffeine makes it harder to sleep"
"Magnesium improves sleep"
"Lack of sleep increases cancer risk"
"Exercise reduces anxiety"

INVALID examples:
"I can't sleep"
"My sleep schedule is bad"
"I went to the doctor because I couldn't sleep"
"Sleep is important"
"Overstimulation makes me overstimulated"
"Use this app to track sleep"
Personal circumstances without a general health relationship are INVALID.

Rules:
1. Do not invent anything.
2. exposure_quote must be copied EXACTLY from the post.
3. outcome_quote must be copied EXACTLY from the post.
4. The two quotes must describe a meaningful health relationship.
5. Do not use truncated phrases ending in "..." or "…".
6. Do not create tautologies.
7. Product/app claims count only if the post explicitly claims a health outcome.
8. If the post does not contain a specific evidence-checkable claim,
   return is_health_claim=false.

Return JSON only:

{{
  "is_health_claim": true,
  "canonical_claim": "specific neutral claim",
  "exposure_quote": "exact source phrase",
  "outcome_quote": "exact source phrase"
}}
"""

    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0}
            },
            timeout=180
        )
        r.raise_for_status()
        result = json.loads(r.json()["response"])
    except Exception:
        continue

    if result.get("is_health_claim") is not True:
        continue

    exposure = normalize(result.get("exposure_quote", ""))
    outcome = normalize(result.get("outcome_quote", ""))
    canonical = normalize(result.get("canonical_claim", ""))

    # Exact grounding
    if exposure.lower() not in post.lower():
        continue

    if outcome.lower() not in post.lower():
        continue

    if bad_quote(exposure) or bad_quote(outcome):
        continue

    if not canonical:
        continue

    # Reject near-tautologies such as
    # "overstimulation -> overstimulated"
    exp_words = set(re.findall(r"[a-z]+", exposure.lower()))
    out_words = set(re.findall(r"[a-z]+", outcome.lower()))

    if exp_words and out_words:
        overlap = len(exp_words & out_words) / min(
            len(exp_words),
            len(out_words)
        )

        if overlap > 0.8:
            continue

    grounded.append({
        "original_post": post,
        "canonical_claim": canonical,
        "exposure_quote": exposure,
        "outcome_quote": outcome
    })


with open("data/processed/grounded_claims.json", "w") as f:
    json.dump(grounded, f, indent=2)

print(f"\nVALID GROUNDED HEALTH CLAIMS: {len(grounded)}\n")

for i, item in enumerate(grounded, 1):
    print("=" * 80)
    print(f"CLAIM {i}")
    print("Canonical:", item["canonical_claim"])
    print("Exposure:", item["exposure_quote"])
    print("Outcome:", item["outcome_quote"])
    print("Source:", item["original_post"][:500])
    print()
