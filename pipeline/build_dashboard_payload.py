import json

def load(name):
    with open(name) as f:
        return json.load(f)

top = load("data/processed/top_narratives.json")
diffusion = load("data/processed/narrative_profiles.json")
dna = load("data/processed/meme_dna_profiles.json")
evidence = load("data/processed/narrative_evidence_verdicts.json")
med = load("data/processed/med_profiles.json")
behavior = load("data/processed/behavior_profiles.json")
priority = load("data/processed/priority_profiles.json")

def by_rank(data):
    return {x["rank"]: x for x in data}

diffusion_map = by_rank(diffusion)
dna_map = by_rank(dna)
evidence_map = by_rank(evidence)
med_map = by_rank(med)
behavior_map = by_rank(behavior)
priority_map = by_rank(priority)

with open("data/processed/pipeline_context.json") as f:
    context = json.load(f)

payload = {
    "keyword": context["keyword"],
    "observation_window": context["observation_window"],
    "narratives": []
}

for rank, narrative in enumerate(top, 1):

    payload["narratives"].append({
        "rank": rank,
        "claim": narrative["claim"],
        "maturity": priority_map[rank]["maturity"],

        "diffusion": {
            "observed_posts": diffusion_map[rank]["observed_posts"],
            "unique_participants": diffusion_map[rank]["unique_participants"],
            "first_seen": diffusion_map[rank]["first_seen"],
            "last_seen": diffusion_map[rank]["last_seen"],
            "persistence_minutes": diffusion_map[rank]["persistence_minutes"],
            "posts_per_hour": diffusion_map[rank]["posts_per_hour"],
            "max_retweets": diffusion_map[rank]["max_retweets"],
            "max_likes": diffusion_map[rank]["max_likes"],
            "max_views": diffusion_map[rank]["max_views"]
        },

        "meme_dna": {
            "distinct_variants": dna_map[rank]["distinct_variants"],
            "mutation_status": dna_map[rank]["mutation_status"],
            "variants": dna_map[rank]["variants"],
            "mutations": dna_map[rank]["mutations"]
        },

        "evidence": {
            "verdict": evidence_map[rank]["verdict"],
            "summary": evidence_map[rank]["summary"],
            "sources": evidence_map[rank]["sources"]
        },

        "divergence": {
            "alignment": med_map[rank]["evidence_alignment"],
            "level": med_map[rank]["meme_evidence_divergence"]
        },

        "behavior": {
            "detected": behavior_map[rank]["behavior_detected"],
            "posts": behavior_map[rank]["behavior_posts"],
            "rate": behavior_map[rank]["behavior_rate"]
        },

        "priority": {
            "flag": priority_map[rank]["flag"],
            "label": priority_map[rank]["priority"],
            "rationale": priority_map[rank]["rationale"]
        }
    })

with open("data/runtime/dashboard_payload.json", "w") as f:
    json.dump(payload, f, indent=2)

print("\nDASHBOARD PAYLOAD READY\n")
print("Keyword:", payload["keyword"])
print("Narratives:", len(payload["narratives"]))

for n in payload["narratives"]:
    print(
        f"{n['rank']}. "
        f"{n['priority']['flag']} "
        f"{n['claim']} "
        f"[{n['maturity']}]"
    )

print("\nSaved to dashboard_payload.json")
