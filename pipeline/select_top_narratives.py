import json

with open("data/processed/ranked_narratives.json") as f:
    ranked = json.load(f)

top3 = ranked[:3]

with open("data/processed/top_narratives.json", "w") as f:
    json.dump(top3, f, indent=2)

print("\nTOP 3 OBSERVED HEALTH NARRATIVES\n")

for i, item in enumerate(top3, 1):
    print("=" * 90)
    print(f"NARRATIVE {i}")
    print("Claim:", item["claim"])
    print("Maturity:", item["status"])
    print("Observed posts:", item["observed_posts"])
    print("Unique participants:", item["unique_authors"])
    print("Max observed reposts:", item["max_retweets"])
    print()

print("Saved to top_narratives.json")
