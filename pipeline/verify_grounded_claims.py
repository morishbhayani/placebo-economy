import json
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"

with open("data/processed/grounded_claims.json") as f:
    claims = json.load(f)

verified = []

print("\nVERIFYING GROUNDED CLAIMS\n")

for i, item in enumerate(claims, 1):

    post = item["original_post"]
    proposed = item["canonical_claim"]

    prompt = f"""
You are verifying whether a proposed health claim is actually supported
by the exact wording of a social-media post.

ORIGINAL POST:
{post}

PROPOSED CLAIM:
{proposed}

Your task is ONLY textual grounding.
Do NOT decide whether the medical claim is scientifically true.

KEEP only if the original post clearly states or directly implies
the proposed relationship.

REJECT if ANY of these occur:

- the proposed claim introduces a concept not present in the post
- cause and effect are reversed
- a personal sequence of events is turned into causation
- the post merely mentions two things together
- the proposed claim exaggerates the source
- the proposed claim is a tautology
- the claim is based on incomplete/truncated text
- the post is just an advertisement, joke, story, prayer, or conversation
  without a specific evidence-checkable health relationship

Examples:

POST:
"I was diagnosed with postpartum psychosis and didn't sleep for 71 hours."
CLAIM:
"Lack of sleep causes postpartum psychosis."
→ REJECT. Direction of causality is not stated.

POST:
"I drank coffee and now I can't sleep."
CLAIM:
"Coffee disrupted my sleep."
→ KEEP as an observed personal claim.

POST:
"I will lie down and fall asleep in peace because You alone, LORD..."
CLAIM:
"Lack of sleep increases depression risk."
→ REJECT. The claim is invented.

POST:
"62% work over 36 hours. 86% report severe sleep deprivation."
CLAIM:
"Long working hours are associated with sleep deprivation."
→ KEEP, but use cautious association language.

If the idea is supported but the proposed wording overstates it,
return REWRITE with a more faithful canonical claim.

Return JSON only:

{{
  "decision": "KEEP",
  "canonical_claim": "faithful concise claim",
  "reason": "short reason"
}}

decision must be exactly:
KEEP
REWRITE
REJECT
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

    except Exception as e:
        print(f"{i}. ERROR:", e)
        continue

    decision = str(result.get("decision", "")).upper()
    canonical = str(result.get("canonical_claim", "")).strip()
    reason = str(result.get("reason", "")).strip()

    print("=" * 80)
    print(f"CLAIM {i}: {decision}")
    print("Original proposal:", proposed)
    print("Verified claim:", canonical)
    print("Reason:", reason)

    if decision in {"KEEP", "REWRITE"} and canonical:
        verified.append({
            **item,
            "canonical_claim": canonical,
            "verification": decision
        })

with open("data/processed/verified_claims.json", "w") as f:
    json.dump(verified, f, indent=2)

print(f"\nVERIFIED CLAIMS RETAINED: {len(verified)}")
print("Saved to verified_claims.json")
