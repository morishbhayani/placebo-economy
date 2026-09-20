import sys
import shutil
import subprocess
from pathlib import Path

if len(sys.argv) < 2:
    print("Missing keyword.", file=sys.stderr)
    sys.exit(1)

keyword = sys.argv[1].strip()
normalized = keyword.lower()


# ---------------------------------------------------------
# VALIDATED DEMO PATH
# Always use the frozen vaccine analysis.
# This keeps the judge demo deterministic and instant.
# ---------------------------------------------------------

if normalized in {"vaccine", "vaccines"}:

    dashboard_cache = Path(
        "data/demo/vaccine_dashboard.json"
    )

    scan_cache = Path(
        "data/demo/vaccine_fast_scan.json"
    )

    if not dashboard_cache.exists():
        print(
            "Vaccine demo cache is missing.",
            file=sys.stderr
        )
        sys.exit(1)

    shutil.copy2(
        dashboard_cache,
        "data/runtime/dashboard_payload.json"
    )

    if scan_cache.exists():
        shutil.copy2(
            scan_cache,
            "data/runtime/fast_scan_results.json"
        )

    print("Loaded validated vaccine analysis.")
    sys.exit(0)


# ---------------------------------------------------------
# LIVE LOCAL FAST SCAN
# ---------------------------------------------------------

parquet_files = list(
    Path(".").glob("data/raw/tweets-*.parquet")
)

if parquet_files:

    result = subprocess.run(
        [sys.executable, "fast_scan.py", keyword]
    )

    sys.exit(result.returncode)


# ---------------------------------------------------------
# DEPLOYED DEMO WITHOUT RAW DATA
# ---------------------------------------------------------

print(
    "LIVE_DATASET_UNAVAILABLE: "
    "The hosted demo does not ship the full social dataset. "
    "Use the validated demo keyword 'vaccine'.",
    file=sys.stderr
)

sys.exit(2)
