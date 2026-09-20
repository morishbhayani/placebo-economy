import sys
import json
import subprocess
import time

if len(sys.argv) < 2:
    print("Usage: python3 run_pipeline.py <healthcare keyword>")
    sys.exit(1)

PYTHON = sys.executable

keyword = " ".join(sys.argv[1:]).strip()

if not keyword:
    print("Please provide a healthcare keyword.")
    sys.exit(1)

print("\n" + "=" * 90)
print("PLACEBO ECONOMY")
print("Analyzing keyword:", keyword)
print("=" * 90 + "\n")

# Save the current keyword so the final dashboard payload
# knows which analysis it represents.
with open("data/processed/pipeline_context.json", "w") as f:
    json.dump({
        "keyword": keyword,
        "observation_window": {
            "first": "2026-08-16 20:00:00-04:00",
            "last": "2026-08-17 02:13:54-04:00"
        }
    }, f, indent=2)


steps = [
    (
        "Discovering health claims",
        [PYTHON, "pipeline/meme_discovery.py", keyword]
    ),
    (
        "Grounding extracted claims",
        [PYTHON, "pipeline/grounded_claim_extractor.py"]
    ),
    (
        "Verifying grounded claims",
        [PYTHON, "pipeline/verify_grounded_claims.py"]
    ),
    (
        "Applying strict claim guardrails",
        [PYTHON, "pipeline/strict_claim_guard.py"]
    ),
    (
        "Building searchable health pool",
        [PYTHON, "pipeline/build_health_pool.py", keyword]
    ),
    (
        "Finding possible meme repetitions",
        [PYTHON, "pipeline/find_meme_matches.py"]
    ),
    (
        "Applying conservative recurrence threshold",
        [PYTHON, "pipeline/strict_meme_recurrence.py"]
    ),
    (
        "Ranking observed narratives",
        [PYTHON, "pipeline/rank_narratives.py"]
    ),
    (
        "Selecting Top 3 narratives",
        [PYTHON, "pipeline/select_top_narratives.py"]
    ),
    (
        "Building diffusion profiles",
        [PYTHON, "pipeline/build_narrative_profiles.py"]
    ),
    (
        "Building Meme DNA",
        [PYTHON, "pipeline/build_meme_dna.py"]
    ),
    (
        "Retrieving scientific evidence",
        [PYTHON, "pipeline/retrieve_narrative_evidence.py"]
    ),
    (
        "Ranking evidence",
        [PYTHON, "pipeline/rank_evidence_semantically.py"]
    ),
    (
        "Building evidence verdicts",
        [PYTHON, "pipeline/build_evidence_verdicts.py"]
    ),
    (
        "Computing Meme–Evidence Divergence",
        [PYTHON, "pipeline/build_med_profiles.py"]
    ),
    (
        "Detecting behavior signals",
        [PYTHON, "pipeline/build_behavior_profiles.py"]
    ),
    (
        "Building public-health priority",
        [PYTHON, "pipeline/build_priority_profiles.py"]
    ),
    (
        "Building dashboard payload",
        [PYTHON, "pipeline/build_dashboard_payload.py"]
    ),
]


start = time.time()

for number, (name, command) in enumerate(steps, 1):

    print("\n" + "=" * 90)
    print(f"[{number}/{len(steps)}] {name}")
    print("=" * 90)

    result = subprocess.run(command)

    if result.returncode != 0:
        print("\nPIPELINE STOPPED")
        print("Failed step:", name)
        sys.exit(result.returncode)


elapsed = time.time() - start

print("\n" + "=" * 90)
print("ANALYSIS COMPLETE")
print("=" * 90)
print("Keyword:", keyword)
print(f"Runtime: {elapsed / 60:.1f} minutes")
print("Dashboard data: dashboard_payload.json")
