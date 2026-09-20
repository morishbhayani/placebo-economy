import json
import re
from datetime import datetime

with open("data/processed/top_narratives.json") as f:
    top = json.load(f)

with open("data/processed/strict_claims.json") as f:
    strict_claims = json.load(f)

with open("data/processed/final_meme_candidates.json") as f:
    meme_candidates = json.load(f)

with open("data/processed/health_candidate_pool.json") as f:
    pool = json.load(f)


def normalize(text):
    text = str(text).replace("—", "-").replace("–", "-")
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


pool_by_text = {}
pool_by_id = {}

for post in pool:
    pool_by_text.setdefault(normalize(post["text"]), []).append(post)
    pool_by_id[str(post["id"])] = post


# Match canonical claims to their original strict seed
strict_by_claim = {
    normalize(x["canonical_claim"]): x
    for x in strict_claims
}

candidate_by_claim = {
    normalize(x["claim"]): x
    for x in meme_candidates
}

profiles = []

print("\nTOP 3 NARRATIVE DIFFUSION PROFILES\n")

for rank, narrative in enumerate(top, 1):

    claim = narrative["claim"]

    seed = strict_by_claim.get(normalize(claim))
    candidate = candidate_by_claim.get(normalize(claim))

    family_posts = []

    # Original/exact repetitions
    if seed:
        key = normalize(seed["original_post"])
        family_posts.extend(pool_by_text.get(key, []))

    # High-confidence paraphrase repetitions
    if candidate:
        for match in candidate.get("matches", []):
            post = pool_by_id.get(str(match["id"]))
            if post:
                family_posts.append(post)

    # Deduplicate true tweet IDs
    family_posts = list({
        str(p["id"]): p
        for p in family_posts
    }.values())

    family_posts.sort(
        key=lambda p: p["created_at"]
    )

    authors = {
        str(p["author_id"])
        for p in family_posts
    }

    times = [
        datetime.fromisoformat(str(p["created_at"]))
        for p in family_posts
    ]

    if len(times) >= 2:
        persistence_minutes = (
            times[-1] - times[0]
        ).total_seconds() / 60

        hours = max(
            persistence_minutes / 60,
            1 / 60
        )

        posts_per_hour = len(family_posts) / hours

    else:
        persistence_minutes = 0
        posts_per_hour = None

    # Normalized textual variants
    variants = {}

    for p in family_posts:
        key = normalize(p["text"])
        variants.setdefault(key, []).append(p)

    profile = {
        "rank": rank,
        "claim": claim,
        "status": narrative["status"],
        "observed_posts": len(family_posts),
        "unique_participants": len(authors),
        "first_seen": (
            str(family_posts[0]["created_at"])
            if family_posts else None
        ),
        "last_seen": (
            str(family_posts[-1]["created_at"])
            if family_posts else None
        ),
        "persistence_minutes": round(
            persistence_minutes, 2
        ),
        "posts_per_hour": (
            round(posts_per_hour, 2)
            if posts_per_hour is not None
            else None
        ),
        "distinct_text_variants": len(variants),
        "max_retweets": max(
            (p["retweet_count"] for p in family_posts),
            default=0
        ),
        "max_likes": max(
            (p["like_count"] for p in family_posts),
            default=0
        ),
        "max_views": max(
            (p["views_count"] for p in family_posts),
            default=0
        ),
        "posts": family_posts
    }

    profiles.append(profile)

    print("=" * 90)
    print(f"NARRATIVE {rank}")
    print("Claim:", claim)
    print("Maturity:", profile["status"])
    print("Observed posts:", profile["observed_posts"])
    print("Unique participants:", profile["unique_participants"])
    print("Distinct text variants:", profile["distinct_text_variants"])
    print("First seen:", profile["first_seen"])
    print("Last seen:", profile["last_seen"])
    print("Persistence:", profile["persistence_minutes"], "minutes")
    print(
        "Diffusion velocity:",
        profile["posts_per_hour"],
        "posts/hour"
        if profile["posts_per_hour"] is not None
        else ""
    )
    print("Max observed reposts:", profile["max_retweets"])
    print("Max likes:", profile["max_likes"])
    print("Max views:", profile["max_views"])
    print()


with open("data/processed/narrative_profiles.json", "w") as f:
    json.dump(profiles, f, indent=2)

print("Saved to narrative_profiles.json")
