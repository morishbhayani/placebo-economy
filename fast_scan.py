import sys
import re
import json
import duckdb
from collections import defaultdict

if len(sys.argv) < 2:
    print("Usage: python3 fast_scan.py <keyword>")
    sys.exit(1)

keyword = " ".join(sys.argv[1:]).strip().lower()

# Words that make a post more likely to contain a health proposition.
HEALTH_TERMS = [
    "cause", "causes", "caused",
    "risk", "risks",
    "increase", "increases", "increased",
    "reduce", "reduces", "reduced",
    "improve", "improves", "improved",
    "help", "helps",
    "harm", "harmful",
    "benefit", "benefits",
    "linked", "associated",
    "study", "research",
    "treat", "treatment",
    "prevent", "prevents", "prevention",
    "side effect", "symptom",
    "mortality", "disease", "health",
    "sleep", "anxiety", "depression",
    "cancer", "pain", "heart",
    "blood", "brain", "immune"
]

def normalize(text):
    text = str(text)
    text = re.sub(r'^RT @[^:]+:\s*', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

query = """
WITH latest AS (
    SELECT *
    FROM (
        SELECT
            id,
            author_id,
            body,
            created_at,
            like_count,
            retweet_count,
            views_count,
            version,
            ROW_NUMBER() OVER (
                PARTITION BY id
                ORDER BY version DESC
            ) rn
        FROM read_parquet('data/raw/tweets-*.parquet', union_by_name=true)
        WHERE lang = 'en'
          AND lower(body) LIKE ?
    )
    WHERE rn = 1
)
SELECT
    id,
    author_id,
    body,
    created_at,
    like_count,
    retweet_count,
    views_count
FROM latest
"""

df = duckdb.execute(
    query,
    [f"%{keyword}%"]
).df()

groups = defaultdict(list)

for _, row in df.iterrows():

    text = normalize(row["body"])
    lower = text.lower()

    # Conservative deterministic health relevance filter
    if not any(term in lower for term in HEALTH_TERMS):
        continue

    # A topic mention alone is not a health claim.
    # Require multiple health concepts AND an explicit relationship.

    HEALTH_CONCEPTS = [
        "sleep", "insomnia", "snoring", "apnea",
        "exercise", "walking", "mortality",
        "metabolic", "hrv", "heart", "blood",
        "brain", "dementia", "mood",
        "anxiety", "depression",
        "cancer", "autism",
        "vaccine", "vaccination",
        "immune", "infection", "covid", "flu",
        "pain", "disease", "symptom",
        "diabetes", "obesity", "cholesterol",
        "blood pressure", "stroke",
        "diet", "nutrition", "weight",
        "medication", "treatment",
        "side effect", "bedbug", "bedbugs"
    ]

    concept_hits = {
        concept
        for concept in HEALTH_CONCEPTS
        if re.search(
            r"\b" + re.escape(concept) + r"\b",
            lower
        )
    }

    # One health word like "sleep" is not enough.
    if len(concept_hits) < 2:
        continue

    RELATIONSHIP_PATTERNS = [
        r"\bcaus(?:e|es|ed|ing)\b",
        r"\binduc(?:e|es|ed|ing)\b",
        r"\blink(?:s|ed|ing)?\b",
        r"\bassociat(?:e|es|ed|ing|ion)\b",
        r"\bincreas(?:e|es|ed|ing)\b",
        r"\breduc(?:e|es|ed|ing)\b",
        r"\bimprov(?:e|es|ed|ing)\b",
        r"\brais(?:e|es|ed|ing)\b",
        r"\blower(?:s|ed|ing)?\b",
        r"\bhigher risk\b",
        r"\blower risk\b",
        r"\brisk of\b",
        r"\bodds of\b",
        r"\brate of\b",
        r"\bprevent(?:s|ed|ing|ion)?\b",
        r"\btreat(?:s|ed|ing|ment)?\b",
        r"\baffect(?:s|ed|ing)?\b",
        r"\bbenefit(?:s|ed|ing)?\b",
        r"\bharm(?:s|ed|ing|ful)?\b",
        r"\bstudy (?:found|finds|shows|showed)\b",
        r"\bresearch (?:found|finds|shows|showed)\b",
        r"\bevidence (?:shows|showed|suggests|suggested)\b"
    ]

    if not any(
        re.search(pattern, lower)
        for pattern in RELATIONSHIP_PATTERNS
    ):
        continue

    # Remove a few obvious figurative/platform uses.
    NON_HEALTH_PHRASES = [
        "whatever helps you sleep at night",
        "@x @safety",
        "avoiding suspension",
        "incite hatred"
    ]

    if any(
        phrase in lower
        for phrase in NON_HEALTH_PHRASES
    ):
        continue

    # The searched concept must participate in the health claim.
    # Examine sentence/clause-sized pieces containing the keyword
    # and require another health concept + relationship language.
    segments = re.split(r"[.!?;\\n]+", lower)

    keyword_claim_found = False

    for segment in segments:

        if keyword not in segment:
            continue

        segment_concepts = {
            concept
            for concept in HEALTH_CONCEPTS
            if re.search(
                r"\b" + re.escape(concept) + r"\b",
                segment
            )
        }

        # Do not count the query term itself as the second concept.
        other_concepts = {
            concept
            for concept in segment_concepts
            if concept not in keyword
            and keyword not in concept
        }

        has_relationship = any(
            re.search(pattern, segment)
            for pattern in RELATIONSHIP_PATTERNS
        )

        if other_concepts and has_relationship:
            keyword_claim_found = True
            break

    if not keyword_claim_found:
        continue

    # Exact/near-exact transmission family
    key = re.sub(r'[^a-z0-9 ]+', '', lower)
    key = re.sub(r'\s+', ' ', key).strip()

    if len(key) < 25:
        continue

    groups[key].append({
        "id": str(row["id"]),
        "author_id": str(row["author_id"]),
        "text": text,
        "created_at": str(row["created_at"]),
        "retweet_count": int(row["retweet_count"] or 0),
        "like_count": int(row["like_count"] or 0),
        "views_count": int(row["views_count"] or 0)
    })

families = []

for posts in groups.values():

    authors = {p["author_id"] for p in posts}

    representative = posts[0]["text"]

    families.append({
        "claim": representative,
        "status": (
            "REPEATED_MEME"
            if len(posts) >= 2 and len(authors) >= 2
            else "EMERGING_CLAIM"
        ),
        "observed_posts": len(posts),
        "unique_authors": len(authors),
        "max_retweets": max(p["retweet_count"] for p in posts),
        "max_likes": max(p["like_count"] for p in posts),
        "max_views": max(p["views_count"] for p in posts),
        "posts": posts
    })

# ---------------------------------------------------------
# MERGE SEMANTICALLY DUPLICATE MEME FAMILIES
# ---------------------------------------------------------

if len(families) > 1:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    # FAST-SCAN PERFORMANCE GUARD
    # Broad keywords can create thousands of exact-text families.
    # Only the strongest recurring families need semantic merging.
    families = sorted(
        families,
        key=lambda x: (
            x.get("observed_posts", 0),
            x.get("unique_authors", 0),
            x.get("max_retweets", 0)
        ),
        reverse=True
    )[:150]

    model = SentenceTransformer("all-MiniLM-L6-v2")

    texts = [
        family["claim"]
        for family in families
    ]

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False
    )

    used = set()
    merged_families = []

    # Conservative merge threshold:
    # merge only very similar narrative variants.
    MERGE_THRESHOLD = 0.70

    for i, family in enumerate(families):

        if i in used:
            continue

        cluster = [family]
        used.add(i)

        for j in range(i + 1, len(families)):

            if j in used:
                continue

            similarity = float(
                np.dot(
                    embeddings[i],
                    embeddings[j]
                )
            )

            # Require both semantic similarity AND meaningful
            # lexical overlap so generic health topics do not collapse.
            STOPWORDS = {
                "the", "a", "an", "and", "or", "to", "of", "in",
                "for", "is", "are", "was", "were", "be", "been",
                "with", "that", "this", "they", "their", "have",
                "has", "had", "from", "on", "if", "it", "as",
                "by", "at", "not", "but", "will", "can", "may",
                "health", "people"
            }

            words_i = {
                w for w in re.findall(r"[a-z0-9]+", family["claim"].lower())
                if len(w) >= 3 and w not in STOPWORDS
            }

            words_j = {
                w for w in re.findall(r"[a-z0-9]+", families[j]["claim"].lower())
                if len(w) >= 3 and w not in STOPWORDS
            }

            shared_terms = words_i & words_j

            if (
                similarity >= MERGE_THRESHOLD
                and len(shared_terms) >= 3
            ):
                cluster.append(families[j])
                used.add(j)

        all_posts = []

        for member in cluster:
            all_posts.extend(member["posts"])

        # Only remove duplicate tweet IDs.
        all_posts = list({
            str(p["id"]): p
            for p in all_posts
        }.values())

        authors = {
            str(p["author_id"])
            for p in all_posts
        }

        # Display wording = fullest available version in the
        # merged meme family. Prevalence still determines ranking/counts.
        representative = max(
            cluster,
            key=lambda x: (
                len(x.get("claim", "")),
                x.get("observed_posts", 0)
            )
        )

        # For display, use the fullest source wording available
        # anywhere inside this merged meme family.
        display_post = max(
            all_posts,
            key=lambda p: len(p.get("text", ""))
        ) if all_posts else None

        display_claim = (
            display_post.get("text", "")
            if display_post
            else representative["claim"]
        )

        # Remove retweet prefix for cleaner presentation.
        display_claim = re.sub(
            r"^RT\s+@[^:]+:\s*",
            "",
            display_claim,
            flags=re.IGNORECASE
        ).strip()

        merged_families.append({
            "claim": display_claim,
            "status": (
                "REPEATED_MEME"
                if len(all_posts) >= 2 and len(authors) >= 2
                else "EMERGING_CLAIM"
            ),
            "observed_posts": len(all_posts),
            "unique_authors": len(authors),
            "max_retweets": max(
                (p["retweet_count"] for p in all_posts),
                default=0
            ),
            "max_likes": max(
                (p["like_count"] for p in all_posts),
                default=0
            ),
            "max_views": max(
                (p["views_count"] for p in all_posts),
                default=0
            ),
            "merged_variants": len(cluster),
            "posts": all_posts
        })

    families = merged_families

families.sort(
    key=lambda x: (
        x["observed_posts"],
        x["unique_authors"],
        x["max_retweets"],
        x["max_likes"],
        x["max_views"]
    ),
    reverse=True
)

# Prefer repeated narratives.
repeated = [
    x for x in families
    if x["status"] == "REPEATED_MEME"
]

emerging = [
    x for x in families
    if x["status"] == "EMERGING_CLAIM"
]

top = (repeated + emerging)[:3]

result = {
    "keyword": keyword,
    "total_matching_posts": len(df),
    "mode": "FAST_SCAN",
    "narratives": top
}

with open("data/runtime/fast_scan_results.json", "w") as f:
    json.dump(result, f, indent=2)

print("\nFAST SCAN COMPLETE")
print("Keyword:", keyword)
print("Matching posts:", len(df))
print("Narratives:", len(top))

for i, item in enumerate(top, 1):
    print()
    print(i, item["status"])
    print("Posts:", item["observed_posts"])
    print("Authors:", item["unique_authors"])
    print(item["claim"][:300])

print("\nSaved to fast_scan_results.json")

# ---------------------------------------------------------
# BUILD FAST DASHBOARD PAYLOAD
# ---------------------------------------------------------

if len(df):
    first_seen_all = str(df["created_at"].min())
    last_seen_all = str(df["created_at"].max())
else:
    first_seen_all = None
    last_seen_all = None

dashboard_payload = {
    "keyword": keyword,
    "mode": "FAST_SCAN",
    "observation_window": {
        "first": first_seen_all,
        "last": last_seen_all
    },
    "narratives": []
}

for rank, family in enumerate(top, 1):

    posts = family["posts"]

    times = sorted(
        [p["created_at"] for p in posts]
    )

    if len(times) >= 2:
        import pandas as pd

        first = pd.to_datetime(times[0])
        last = pd.to_datetime(times[-1])

        persistence_minutes = (
            last - first
        ).total_seconds() / 60

        hours = max(
            persistence_minutes / 60,
            1 / 60
        )

        posts_per_hour = len(posts) / hours

    else:
        persistence_minutes = 0
        posts_per_hour = None

    repeated = family["status"] == "REPEATED_MEME"

    dashboard_payload["narratives"].append({
        "rank": rank,
        "claim": family["claim"],
        "maturity": family["status"],

        "diffusion": {
            "observed_posts": family["observed_posts"],
            "unique_participants": family["unique_authors"],
            "first_seen": times[0] if times else None,
            "last_seen": times[-1] if times else None,
            "persistence_minutes": round(
                persistence_minutes, 2
            ),
            "posts_per_hour": (
                round(posts_per_hour, 2)
                if posts_per_hour is not None
                else None
            ),
            "max_retweets": family["max_retweets"],
            "max_likes": family["max_likes"],
            "max_views": family["max_views"]
        },

        "meme_dna": {
            "distinct_variants": 1,
            "mutation_status": (
                "REPLICATION_WITHOUT_OBSERVED_MUTATION"
                if repeated
                else "INSUFFICIENT_FOR_MUTATION_ANALYSIS"
            ),
            "variants": [{
                "variant": "V1",
                "text": family["claim"],
                "observed_count": family["observed_posts"],
                "unique_authors": family["unique_authors"]
            }],
            "mutations": []
        },

        # Deep scientific analysis deliberately not fabricated
        # during Fast Scan.
        "evidence": {
            "verdict": "NOT_RUN_FAST_SCAN",
            "summary": (
                "Scientific evidence analysis is not run during Fast Scan. "
                "Fast Scan prioritizes immediate cultural-signal discovery."
            ),
            "sources": []
        },

        "divergence": {
            "alignment": "NOT_ANALYZED",
            "level": "UNRESOLVED"
        },

        "behavior": {
            "detected": False,
            "posts": 0,
            "rate": 0
        },

        "priority": {
            "flag": "🔵" if repeated else "⚪",
            "label": (
                "REPEATED_NARRATIVE"
                if repeated
                else "EMERGING_CLAIM"
            ),
            "rationale": (
                "Repeated independently in the observed dataset."
                if repeated
                else
                "Observed once in the current window; recurrence "
                "has not yet been established."
            )
        }
    })

with open("data/runtime/dashboard_payload.json", "w") as f:
    json.dump(
        dashboard_payload,
        f,
        indent=2
    )

print("Fast dashboard payload written.")
