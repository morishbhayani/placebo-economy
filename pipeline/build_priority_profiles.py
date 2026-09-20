import json

with open("data/processed/med_profiles.json") as f:
    med = json.load(f)

with open("data/processed/behavior_profiles.json") as f:
    behavior = json.load(f)

behavior_by_rank = {
    x["rank"]: x
    for x in behavior
}

results = []

print("\nPUBLIC-HEALTH PRIORITY\n")

for item in med:

    rank = item["rank"]
    beh = behavior_by_rank[rank]

    divergence = item["meme_evidence_divergence"]
    repeated = item["maturity"] == "REPEATED_MEME"
    behavior_active = beh["behavior_detected"]

    # Conservative public-health prioritization.
    # We do NOT call something harmful just because it sounds negative.

    if divergence == "LOW":
        priority = "EVIDENCE_ALIGNED"
        flag = "🟢"
        rationale = (
            "The observed narrative is broadly aligned with "
            "the retrieved scientific evidence."
        )

    elif divergence == "UNRESOLVED":
        priority = "EVIDENCE_UNRESOLVED"
        flag = "⚪"
        rationale = (
            "Available evidence is insufficient to determine "
            "alignment confidently."
        )

    elif (
        divergence == "HIGH"
        and repeated
        and behavior_active
    ):
        priority = "PRIORITY_HARMFUL_NARRATIVE"
        flag = "🚨"
        rationale = (
            "The narrative strongly diverges from evidence, "
            "is being repeated, and contains explicit behavioral activation."
        )

    elif divergence == "HIGH" and repeated:
        priority = "HIGH_DIVERGENCE_WATCH"
        flag = "🟠"
        rationale = (
            "The narrative strongly diverges from evidence and "
            "is being repeated, but explicit behavioral activation "
            "was not detected."
        )

    elif divergence == "MODERATE" and behavior_active:
        priority = "BEHAVIOR_ACTIVE_WATCH"
        flag = "🟠"
        rationale = (
            "The claim only partially aligns with retrieved evidence "
            "and includes an explicit recommendation or behavioral signal."
        )

    elif divergence == "MODERATE":
        priority = "WATCH"
        flag = "👀"
        rationale = (
            "The claim only partially aligns with retrieved evidence, "
            "but no explicit behavioral activation was detected."
        )

    else:
        priority = "MONITOR"
        flag = "👀"
        rationale = "The narrative warrants continued monitoring."

    result = {
        "rank": rank,
        "claim": item["claim"],
        "maturity": item["maturity"],
        "observed_posts": item["observed_posts"],
        "evidence_verdict": item["evidence_verdict"],
        "evidence_alignment": item["evidence_alignment"],
        "divergence": divergence,
        "behavior_detected": behavior_active,
        "behavior_rate": beh["behavior_rate"],
        "priority": priority,
        "flag": flag,
        "rationale": rationale
    }

    results.append(result)

    print("=" * 90)
    print(f"NARRATIVE {rank}")
    print("Claim:", result["claim"])
    print("Maturity:", result["maturity"])
    print("Evidence:", result["evidence_verdict"])
    print("Divergence:", divergence)
    print(
        "Behavior signal:",
        "YES" if behavior_active else "NO"
    )
    print("Priority:", flag, priority)
    print("Why:", rationale)
    print()


with open("data/processed/priority_profiles.json", "w") as f:
    json.dump(results, f, indent=2)

print("Saved to priority_profiles.json")
