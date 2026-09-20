import json

with open("narrative_evidence_verdicts.json") as f:
    evidence = json.load(f)

with open("meme_dna_profiles.json") as f:
    dna = json.load(f)

with open("narrative_profiles.json") as f:
    diffusion = json.load(f)

VERDICT_MAP = {
    "SUPPORTED": {
        "alignment": "HIGH",
        "divergence": "LOW"
    },
    "MIXED": {
        "alignment": "PARTIAL",
        "divergence": "MODERATE"
    },
    "REFUTED": {
        "alignment": "VERY_LOW",
        "divergence": "HIGH"
    },
    "INSUFFICIENT": {
        "alignment": "UNKNOWN",
        "divergence": "UNRESOLVED"
    }
}

med_profiles = []

print("\nMEME-EVIDENCE DIVERGENCE\n")

for ev in evidence:

    rank = ev["rank"]

    dna_item = next(
        x for x in dna
        if x["rank"] == rank
    )

    diffusion_item = next(
        x for x in diffusion
        if x["rank"] == rank
    )

    verdict = ev["verdict"]

    mapping = VERDICT_MAP.get(
        verdict,
        {
            "alignment": "UNKNOWN",
            "divergence": "UNRESOLVED"
        }
    )

    profile = {
        "rank": rank,
        "claim": ev["claim"],
        "evidence_verdict": verdict,
        "evidence_alignment": mapping["alignment"],
        "meme_evidence_divergence": mapping["divergence"],
        "evidence_summary": ev["summary"],
        "maturity": diffusion_item["status"],
        "observed_posts": diffusion_item["observed_posts"],
        "unique_participants": diffusion_item[
            "unique_participants"
        ],
        "mutation_status": dna_item["mutation_status"]
    }

    med_profiles.append(profile)

    print("=" * 90)
    print(f"NARRATIVE {rank}")
    print("Claim:", profile["claim"])
    print("Evidence verdict:", verdict)
    print("Evidence alignment:", profile["evidence_alignment"])
    print(
        "Meme-Evidence Divergence:",
        profile["meme_evidence_divergence"]
    )
    print("Maturity:", profile["maturity"])
    print("Observed posts:", profile["observed_posts"])
    print("Mutation:", profile["mutation_status"])
    print()


with open("med_profiles.json", "w") as f:
    json.dump(med_profiles, f, indent=2)

print("Saved to med_profiles.json")
