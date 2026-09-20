import json
import re

with open("data/processed/verified_claims.json") as f:
    claims = json.load(f)

# Relationship language that can support an evidence-checkable health claim.
SOURCE_RELATION_PATTERNS = [
    r"\bcause(?:s|d)?\b",
    r"\bincreas(?:e|es|ed|ing)\b",
    r"\breduc(?:e|es|ed|ing)\b",
    r"\bimprov(?:e|es|ed|ing)\b",
    r"\bhelp(?:s|ed|ing)?\b",
    r"\blink(?:ed|s)?\b",
    r"\bassociat(?:ed|ion)\b",
    r"\brisk\b",
    r"\bprevent(?:s|ed|ion|ing)?\b",
    r"\bleads? to\b",
    r"\bdue to\b",
    r"\bbecause of\b",
    r"\bmakes? me\b",
    r"\bmade me\b",
]

# A canonical meme must itself describe a relationship.
CLAIM_RELATION_PATTERNS = [
    r"\bcause",
    r"\bincreas",
    r"\breduc",
    r"\bimprov",
    r"\bhelp",
    r"\blink",
    r"\bassociat",
    r"\brisk",
    r"\bprevent",
    r"\blead",
    r"\bdisrupt",
    r"\bworsen",
]

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on",
    "for", "with", "is", "are", "may", "can", "be", "being",
    "from", "that", "this"
}

def tokens(text):
    return {
        w for w in re.findall(r"[a-z]+", text.lower())
        if len(w) >= 4 and w not in STOPWORDS
    }

strict = []

print("\nSTRICT CLAIM VALIDATION\n")

for i, item in enumerate(claims, 1):

    source = item["original_post"]
    claim = item["canonical_claim"]

    reasons = []

    # 1. Canonical claim must actually describe a relationship.
    claim_has_relation = any(
        re.search(p, claim, re.I)
        for p in CLAIM_RELATION_PATTERNS
    )

    if not claim_has_relation:
        reasons.append("canonical statement is not a health relationship")

    # 2. The ORIGINAL post must contain explicit relationship language.
    source_has_relation = any(
        re.search(p, source, re.I)
        for p in SOURCE_RELATION_PATTERNS
    )

    if not source_has_relation:
        reasons.append("source does not explicitly state a relationship")

    # 3. Catch major invented concepts.
    source_words = tokens(source)
    claim_words = tokens(claim)

    shared = claim_words & source_words

    if claim_words:
        lexical_support = len(shared) / len(claim_words)
    else:
        lexical_support = 0

    if lexical_support < 0.35:
        reasons.append(
            f"too much unsupported canonical wording "
            f"({lexical_support:.0%} lexical support)"
        )

    if reasons:
        print(f"CLAIM {i}: REJECT")
        print(" ", claim)
        for reason in reasons:
            print("  -", reason)
        print()
        continue

    print(f"CLAIM {i}: KEEP")
    print(" ", claim)
    print()

    strict.append(item)

with open("data/processed/strict_claims.json", "w") as f:
    json.dump(strict, f, indent=2)

print("=" * 80)
print("STRICT CLAIMS RETAINED:", len(strict))
print("Saved to strict_claims.json")
