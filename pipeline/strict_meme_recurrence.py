import json

# Conservative high-confidence threshold for MVP.
# We would rather miss a loose paraphrase than falsely call unrelated
# health claims the same meme.
SIMILARITY_THRESHOLD = 0.75

with open("data/processed/meme_match_candidates.json") as f:
    results = json.load(f)

final = []

print("\nHIGH-CONFIDENCE MEME RECURRENCE\n")

for item in results:

    claim = item["claim"]

    matches = [
        m for m in item["matches"]
        if m["similarity"] >= SIMILARITY_THRESHOLD
    ]

    unique_authors = {
        m["author_id"]
        for m in matches
    }

    if len(unique_authors) >= 1:
        status = "REPEATED_MEME"
    else:
        status = "EMERGING_CLAIM"

    record = {
        "seed_number": item["seed_number"],
        "claim": claim,
        "status": status,
        "additional_matching_posts": len(matches),
        "additional_authors": len(unique_authors),
        "matches": matches
    }

    final.append(record)

    print("=" * 90)
    print(f"SEED {item['seed_number']}")
    print("Claim:", claim)
    print("Status:", status)
    print("Additional high-confidence matches:", len(matches))
    print("Additional authors:", len(unique_authors))

    for match in matches:
        print(
            f"  - similarity={match['similarity']:.3f}: "
            f"{match['text'][:400]}"
        )

    print()

with open("data/processed/final_meme_candidates.json", "w") as f:
    json.dump(final, f, indent=2)

print("Saved to final_meme_candidates.json")
