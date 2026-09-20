import json
import re

with open("data/processed/narrative_profiles.json") as f:
    profiles = json.load(f)

PATTERNS = {
    "RECOMMENDATION": [
        r"\byou should\b",
        r"\byou need to\b",
        r"\bshould try\b",
        r"\btry to\b",
        r"\btry for\b",
        r"\baim for\b",
        r"\brecommend(?:s|ed|ing)?\b",
        r"\bavoid (?:taking|using|eating|drinking|doing)\b",
        r"\bdo not (?:take|use|eat|drink|stop|start)\b",
        r"\bdon't (?:take|use|eat|drink|stop|start)\b",
        r"\bnever (?:take|use|eat|drink)\b",
    ],
    "SELF_INTENT": [
        r"\bi(?:'m| am) going to\b",
        r"\bi will (?:start|stop|try|take|use|avoid)\b",
        r"\bi(?:'ll) (?:start|stop|try|take|use|avoid)\b",
        r"\bi need to (?:start|stop|try|take|use|avoid)\b",
        r"\bi plan to\b",
        r"\bi'm gonna (?:start|stop|try|take|use|avoid)\b",
    ],
    "TREATMENT_ACTION": [
        r"\bstop taking\b",
        r"\bstart taking\b",
        r"\bstarted taking\b",
        r"\bstopped taking\b",
        r"\bswitch(?:ed)? to\b",
        r"\bquit taking\b",
    ],
}

results = []

print("\nBELIEF → BEHAVIOR SIGNALS\n")

for profile in profiles:

    detected_posts = []

    for post in profile["posts"]:

        text = post["text"]
        signals = []

        for category, patterns in PATTERNS.items():

            for pattern in patterns:

                if re.search(pattern, text, re.I):
                    signals.append(category)
                    break

        signals = sorted(set(signals))

        if signals:
            detected_posts.append({
                "id": post["id"],
                "author_id": post["author_id"],
                "text": text,
                "signals": signals
            })

    observed_posts = profile["observed_posts"]

    behavior_rate = (
        len(detected_posts) / observed_posts
        if observed_posts
        else 0
    )

    result = {
        "rank": profile["rank"],
        "claim": profile["claim"],
        "observed_posts": observed_posts,
        "behavior_posts": len(detected_posts),
        "behavior_rate": round(behavior_rate, 3),
        "behavior_detected": bool(detected_posts),
        "behavior_posts_detail": detected_posts
    }

    results.append(result)

    print("=" * 90)
    print(f"NARRATIVE {profile['rank']}")
    print("Claim:", profile["claim"])
    print("Observed posts:", observed_posts)
    print("Behavior-signal posts:", len(detected_posts))
    print(
        "Behavioral intention/recommendation rate:",
        f"{behavior_rate:.1%}"
    )

    for post in detected_posts:
        print("Signals:", ", ".join(post["signals"]))
        print("Post:", post["text"][:500])

    print()

with open("data/processed/behavior_profiles.json", "w") as f:
    json.dump(results, f, indent=2)

print("Saved to behavior_profiles.json")
