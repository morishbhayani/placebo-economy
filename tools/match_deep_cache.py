import json
from pathlib import Path

with open("data/runtime/fast_scan_results.json") as f:
    scan = json.load(f)

cache_files = list(Path("data/deep_cache").glob("*.json"))

caches = []

for path in cache_files:
    with open(path) as f:
        cache = json.load(f)

    cache["_path"] = str(path)
    caches.append(cache)


def find_cache(text):
    text_lower = text.lower()

    best = None
    best_score = 0

    for cache in caches:

        terms = [
            str(t).lower()
            for t in cache.get("match_terms", [])
        ]

        matched = [
            term for term in terms
            if term in text_lower
        ]

        # Require multiple matching concepts so generic words
        # such as "vaccine" alone cannot trigger a cache.
        score = len(matched)

        has_specific_phrase = any(
            " " in term and term in text_lower
            for term in terms
        )

        if (
            score >= 3
            and has_specific_phrase
            and score > best_score
        ):
            best = cache
            best_score = score

    return best


print("\nDEEP ANALYSIS CACHE MATCHES\n")

for i, narrative in enumerate(scan["narratives"], 1):

    match = find_cache(narrative["claim"])

    print("=" * 80)
    print(f"NARRATIVE {i}")
    print(narrative["claim"][:300])

    if match:
        print("Deep Analysis: AVAILABLE")
        print("Cache:", match["_path"])
        print("Title:", match["title"])
    else:
        print("Deep Analysis: NOT CACHED")

