import json
import numpy as np
from sentence_transformers import SentenceTransformer

with open("data/processed/strict_claims.json") as f:
    seeds = json.load(f)

with open("data/processed/health_candidate_pool.json") as f:
    pool = json.load(f)

# Fix the one malformed canonical label from extraction.
for seed in seeds:
    if seed["canonical_claim"].strip().lower() == "improve rest":
        seed["canonical_claim"] = (
            "Hushd Avera anti-snoring mouthpiece is meant to improve rest"
        )

print("Loading semantic model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

seed_texts = [x["canonical_claim"] for x in seeds]
pool_texts = [x["text"] for x in pool]

seed_embeddings = model.encode(
    seed_texts,
    normalize_embeddings=True,
    show_progress_bar=True
)

pool_embeddings = model.encode(
    pool_texts,
    normalize_embeddings=True,
    show_progress_bar=True
)

results = []

for seed_num, (seed, seed_vec) in enumerate(
    zip(seeds, seed_embeddings), 1
):
    similarities = np.dot(pool_embeddings, seed_vec)

    # Retrieve top semantic candidates.
    order = np.argsort(similarities)[::-1]

    matches = []

    seen_text = set()

    for idx in order:
        post = pool[idx]
        text = post["text"]

        # Don't count the original seed post itself.
        if text.strip() == seed["original_post"].strip():
            continue

        # Avoid identical text appearing multiple times in this preview.
        normalized = text.lower().strip()

        if normalized in seen_text:
            continue

        seen_text.add(normalized)

        matches.append({
            "similarity": float(similarities[idx]),
            "id": post["id"],
            "author_id": post["author_id"],
            "text": text
        })

        if len(matches) == 8:
            break

    results.append({
        "seed_number": seed_num,
        "claim": seed["canonical_claim"],
        "matches": matches
    })


with open("data/processed/meme_match_candidates.json", "w") as f:
    json.dump(results, f, indent=2)


print("\nSEMANTIC MEME-MATCH CANDIDATES\n")

for result in results:

    print("=" * 90)
    print(f"SEED {result['seed_number']}")
    print("CLAIM:", result["claim"])
    print()

    for i, match in enumerate(result["matches"], 1):
        print(
            f"{i}. similarity={match['similarity']:.3f} "
            f"author={match['author_id']}"
        )
        print("  ", match["text"][:500])
        print()

print("Saved to meme_match_candidates.json")
