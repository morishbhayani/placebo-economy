import json
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"

with open("data/processed/meme_match_candidates.json") as f:
    results = json.load(f)

validated_memes = []

for result in results:

    seed_num = result["seed_number"]
    claim = result["claim"]
    matches = result["matches"]

    candidates = "\n\n".join(
        f"""CANDIDATE {i}
POST: {m["text"]}"""
        for i, m in enumerate(matches)
    )

    prompt = f"""
You are deciding whether social-media posts transmit the SAME underlying
health claim as a seed claim.

SEED CLAIM:
{claim}

For each candidate, classify it as:

SAME_CLAIM
- expresses substantially the same health proposition
- wording may differ
- does not need to be an exact copy

RELATED_DIFFERENT
- discusses similar topics but makes a different health claim

UNRELATED
- does not express the seed health claim

STRICT RULES:

1. Shared words are not enough.
2. The exposure/intervention and health outcome must substantially match.
3. Do not merge broad themes such as "exercise is healthy."
4. Do not invent relationships.
5. A narrower or stronger version may still be SAME_CLAIM if the underlying
   proposition remains recognizable.
6. If uncertain, use RELATED_DIFFERENT rather than SAME_CLAIM.

Return JSON only:

{{
  "results": [
    {{
      "candidate": 0,
      "classification": "SAME_CLAIM"
    }}
  ]
}}

CANDIDATES:

{candidates}
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
            timeout=240
        )

        r.raise_for_status()
        response = json.loads(r.json()["response"])

    except Exception as e:
        print(f"Seed {seed_num} failed:", e)
        continue

    same = []

    for decision in response.get("results", []):
        idx = decision.get("candidate")
        classification = str(
            decision.get("classification", "")
        ).upper()

        if (
            classification == "SAME_CLAIM"
            and isinstance(idx, int)
            and 0 <= idx < len(matches)
        ):
            same.append(matches[idx])

    authors = {
        m["author_id"]
        for m in same
    }

    status = (
        "REPEATED_MEME"
        if len(authors) >= 1
        else "EMERGING_CLAIM"
    )

    validated_memes.append({
        "seed_number": seed_num,
        "claim": claim,
        "status": status,
        "matching_posts": len(same),
        "matching_authors": len(authors),
        "matches": same
    })


with open("data/processed/validated_memes.json", "w") as f:
    json.dump(validated_memes, f, indent=2)


print("\nMEME RECURRENCE RESULTS\n")

for item in validated_memes:

    print("=" * 90)
    print(f"SEED {item['seed_number']}")
    print("Claim:", item["claim"])
    print("Status:", item["status"])
    print("Additional matching posts:", item["matching_posts"])
    print("Additional authors:", item["matching_authors"])

    for match in item["matches"]:
        print(
            f"  - similarity={match['similarity']:.3f}: "
            f"{match['text'][:350]}"
        )

    print()
