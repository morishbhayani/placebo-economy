import json
import re
from sentence_transformers import SentenceTransformer
import numpy as np

with open("data/processed/narrative_profiles.json") as f:
    profiles = json.load(f)

def normalize(text):
    text = str(text).replace("—", "-").replace("–", "-")
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

model = SentenceTransformer("all-MiniLM-L6-v2")

dna_profiles = []

print("\nMEME DNA PROFILES\n")

for profile in profiles:

    posts = profile["posts"]

    # Collect genuinely distinct observed textual forms.
    variants = {}

    for post in posts:
        cleaned = normalize(post["text"])
        key = cleaned.lower()

        if key not in variants:
            variants[key] = {
                "text": cleaned,
                "observed_count": 0,
                "authors": set()
            }

        variants[key]["observed_count"] += 1
        variants[key]["authors"].add(str(post["author_id"]))

    variant_list = []

    for i, v in enumerate(variants.values(), 1):
        variant_list.append({
            "variant": f"V{i}",
            "text": v["text"],
            "observed_count": v["observed_count"],
            "unique_authors": len(v["authors"])
        })

    mutations = []

    # Only compute semantic mutation if we actually observed
    # multiple distinct textual forms.
    if len(variant_list) >= 2:

        texts = [v["text"] for v in variant_list]

        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False
        )

        for i in range(len(texts) - 1):

            similarity = float(
                np.dot(
                    embeddings[i],
                    embeddings[i + 1]
                )
            )

            mutation = 1 - similarity

            mutations.append({
                "from": variant_list[i]["variant"],
                "to": variant_list[i + 1]["variant"],
                "cosine_similarity": round(similarity, 3),
                "semantic_mutation": round(mutation, 3)
            })

        mutation_status = "OBSERVED_VARIATION"

    elif profile["observed_posts"] >= 2:

        mutation_status = "REPLICATION_WITHOUT_OBSERVED_MUTATION"

    else:

        mutation_status = "INSUFFICIENT_FOR_MUTATION_ANALYSIS"

    dna = {
        "rank": profile["rank"],
        "claim": profile["claim"],
        "maturity": profile["status"],
        "observed_posts": profile["observed_posts"],
        "distinct_variants": len(variant_list),
        "mutation_status": mutation_status,
        "variants": variant_list,
        "mutations": mutations
    }

    dna_profiles.append(dna)

    print("=" * 90)
    print(f"NARRATIVE {profile['rank']}")
    print("Claim:", profile["claim"])
    print("Observed posts:", profile["observed_posts"])
    print("Distinct variants:", len(variant_list))
    print("Mutation status:", mutation_status)

    for v in variant_list:
        print(
            f"{v['variant']}: "
            f"{v['observed_count']} posts / "
            f"{v['unique_authors']} authors"
        )
        print(" ", v["text"][:500])

    for m in mutations:
        print(
            f"{m['from']} → {m['to']}: "
            f"similarity={m['cosine_similarity']}, "
            f"mutation={m['semantic_mutation']}"
        )

    print()

with open("data/processed/meme_dna_profiles.json", "w") as f:
    json.dump(dna_profiles, f, indent=2)

print("Saved to meme_dna_profiles.json")
