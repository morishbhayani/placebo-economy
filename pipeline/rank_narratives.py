import json
import re

with open("data/processed/final_meme_candidates.json") as f:
    candidates = json.load(f)

with open("data/processed/strict_claims.json") as f:
    strict_claims = json.load(f)

with open("data/processed/health_candidate_pool.json") as f:
    pool = json.load(f)

def normalize(text):
    text = str(text).replace("—", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()

# Index corpus both by text and tweet ID
pool_by_text = {}
pool_by_id = {}

for post in pool:
    key = normalize(post["text"])
    pool_by_text.setdefault(key, []).append(post)
    pool_by_id[str(post["id"])] = post

ranked = []

for candidate in candidates:

    seed_number = candidate["seed_number"]
    seed = strict_claims[seed_number - 1]

    family_posts = []

    # Include ALL occurrences of the exact seed wording.
    # This is important because identical text can be transmitted
    # by multiple independent accounts.
    seed_key = normalize(seed["original_post"])

    family_posts.extend(
        pool_by_text.get(seed_key, [])
    )

    # Add each high-confidence semantic recurrence by its actual tweet ID.
    for match in candidate["matches"]:
        match_id = str(match["id"])

        if match_id in pool_by_id:
            family_posts.append(pool_by_id[match_id])

    # Deduplicate only true duplicate tweet IDs.
    family_posts = list({
        str(post["id"]): post
        for post in family_posts
    }.values())

    authors = {
        str(post["author_id"])
        for post in family_posts
    }

    max_retweets = max(
        (post["retweet_count"] for post in family_posts),
        default=0
    )

    max_likes = max(
        (post["like_count"] for post in family_posts),
        default=0
    )

    max_views = max(
        (post["views_count"] for post in family_posts),
        default=0
    )

    # Final meme maturity is determined from actual observed recurrence,
    # including exact-text transmission AND high-confidence paraphrases.
    if len(family_posts) >= 2 and len(authors) >= 2:
        final_status = "REPEATED_MEME"
    else:
        final_status = "EMERGING_CLAIM"

    ranked.append({
        "claim": candidate["claim"],
        "status": final_status,
        "observed_posts": len(family_posts),
        "unique_authors": len(authors),
        "max_retweets": max_retweets,
        "max_likes": max_likes,
        "max_views": max_views
    })

# Transparent ranking:
# 1. prevalence
# 2. unique participation
# 3. amplification
ranked.sort(
    key=lambda x: (
        x["observed_posts"],
        x["unique_authors"],
        x["max_retweets"],
        x["max_likes"],
        x["max_views"]
    ),
    reverse=True
)

with open("data/processed/ranked_narratives.json", "w") as f:
    json.dump(ranked, f, indent=2)

print("\nRANKED HEALTH NARRATIVES\n")

for i, item in enumerate(ranked, 1):
    print("=" * 90)
    print(f"RANK {i}")
    print("Claim:", item["claim"])
    print("Status:", item["status"])
    print("Observed posts:", item["observed_posts"])
    print("Unique authors:", item["unique_authors"])
    print("Max observed reposts:", item["max_retweets"])
    print("Max likes:", item["max_likes"])
    print("Max views:", item["max_views"])
    print()

print("Saved to ranked_narratives.json")
