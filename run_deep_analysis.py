import sys
import re
import json
from pathlib import Path

import numpy as np
import requests
from sentence_transformers import SentenceTransformer

from llm_client import generate_text


ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "data/runtime/fast_scan_results.json"
CACHE_DIR = ROOT / "data/deep_cache"

EUROPE_PMC = (
    "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
)

CACHE_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# HELPERS
# =========================================================

def extract_json(text):
    text = text.strip()

    # Remove common markdown fences.
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model response")

    return json.loads(text[start:end + 1])


def clean_text(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")[:60]


def build_match_terms(text):
    words = re.findall(r"[a-z0-9]+", text.lower())

    stop = {
        "the", "and", "that", "this", "with", "from",
        "have", "has", "were", "was", "for", "are",
        "but", "not", "into", "they", "their", "you",
        "your", "about", "just", "more", "than"
    }

    meaningful = [
        word for word in words
        if len(word) >= 4 and word not in stop
    ]

    meaningful = list(dict.fromkeys(meaningful))

    terms = meaningful[:8]

    if len(meaningful) >= 2:
        terms.append(
            f"{meaningful[0]} {meaningful[1]}"
        )

    if len(meaningful) >= 3:
        terms.append(
            f"{meaningful[0]} {meaningful[1]} "
            f"{meaningful[2]}"
        )

    return list(dict.fromkeys(terms))


# =========================================================
# LOAD CLICKED NARRATIVE
# =========================================================

if len(sys.argv) < 2:
    print(
        "Usage: python3 run_deep_analysis.py "
        "<rank> [Gemini|Groq|Ollama]"
    )
    sys.exit(1)

rank = int(sys.argv[1])
primary_model = (
    sys.argv[2]
    if len(sys.argv) >= 3
    else "Gemini"
)

with open(RUNTIME) as f:
    scan = json.load(f)

narratives = scan.get("narratives", [])

# Fast Scan stores narratives in ranked list order but may not
# include an explicit "rank" field. Treat the CLI rank as a
# 1-based list position, while still supporting explicit ranks.
narrative = next(
    (
        n for n in narratives
        if int(n.get("rank", 0) or 0) == rank
    ),
    None
)

if narrative is None and 1 <= rank <= len(narratives):
    narrative = narratives[rank - 1]

if narrative is None:
    raise RuntimeError(
        f"Narrative rank {rank} was not found. "
        f"Available narratives: {len(narratives)}"
    )

narrative["rank"] = rank

social_claim = clean_text(
    narrative.get("claim", "")
)

posts = narrative.get("posts", [])

print("\nDEEP ANALYSIS")
print("Primary model:", primary_model)
print("Observed narrative:", social_claim)


# =========================================================
# 1. CANONICAL CLAIM + SEARCH QUERIES
# =========================================================

claim_prompt = f"""
You are analyzing a health narrative observed on social media.

Observed wording:
{social_claim}

Extract the central evidence-checkable HEALTH proposition.

Then generate 3 concise scientific-literature search queries
suitable for Europe PMC / PubMed.

Do not evaluate whether the claim is true yet.
Do not include political or institutional allegations unless
they are themselves part of the health proposition.

Return ONLY valid JSON:

{{
  "canonical_claim": "specific health proposition",
  "queries": [
    "query 1",
    "query 2",
    "query 3"
  ]
}}
"""

try:
    claim_info = extract_json(
        generate_text(
            claim_prompt,
            primary=primary_model,
            max_tokens=512
        )
    )

    canonical_claim = clean_text(
        claim_info["canonical_claim"]
    )

    queries = [
        clean_text(q)
        for q in claim_info.get("queries", [])
        if clean_text(q)
    ][:3]

except Exception as error:
    print(
        "Claim extraction fallback:",
        str(error)[:150]
    )

    canonical_claim = social_claim
    queries = [canonical_claim]

if not queries:
    queries = [canonical_claim]

print("Canonical claim:", canonical_claim)
print("Evidence queries:", queries)


# =========================================================
# 2. EUROPE PMC RETRIEVAL
# =========================================================

papers_by_id = {}

for query in queries:

    params = {
        "query": query,
        "format": "json",
        "resultType": "core",
        "pageSize": 12
    }

    try:
        response = requests.get(
            EUROPE_PMC,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        results = (
            response.json()
            .get("resultList", {})
            .get("result", [])
        )

        for paper in results:

            pmid = (
                paper.get("pmid")
                or paper.get("id")
                or paper.get("doi")
            )

            if not pmid:
                continue

            abstract = clean_text(
                paper.get("abstractText", "")
            )

            title = clean_text(
                paper.get("title", "")
            )

            if not title:
                continue

            papers_by_id[str(pmid)] = {
                "pmid": paper.get("pmid"),
                "title": title,
                "abstract": abstract,
                "year": paper.get("pubYear", ""),
                "journal": paper.get(
                    "journalTitle",
                    ""
                )
            }

    except Exception as error:
        print(
            "Europe PMC query failed:",
            query,
            str(error)[:120]
        )

papers = list(papers_by_id.values())

print("Retrieved papers:", len(papers))


# =========================================================
# 3. SEMANTIC EVIDENCE RANKING
# =========================================================

embedder = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

if papers:

    documents = [
        clean_text(
            paper["title"]
            + " "
            + paper.get("abstract", "")
        )
        for paper in papers
    ]

    claim_embedding = embedder.encode(
        [canonical_claim],
        normalize_embeddings=True,
        show_progress_bar=False
    )[0]

    paper_embeddings = embedder.encode(
        documents,
        normalize_embeddings=True,
        show_progress_bar=False
    )

    similarities = np.dot(
        paper_embeddings,
        claim_embedding
    )

    for paper, score in zip(
        papers,
        similarities
    ):
        paper["semantic_relevance"] = round(
            float(score),
            3
        )

    papers = sorted(
        papers,
        key=lambda p: p[
            "semantic_relevance"
        ],
        reverse=True
    )

top_papers = papers[:5]


# =========================================================
# 4. BUILD OBSERVED MEME VARIANTS
# =========================================================

unique_variants = []

seen = set()

for post in posts:

    text = clean_text(
        post.get("text", "")
    )

    norm = re.sub(
        r"[^a-z0-9]+",
        " ",
        text.lower()
    )

    norm = clean_text(norm)

    if not text or norm in seen:
        continue

    seen.add(norm)
    unique_variants.append(text)

# Prefer fuller wordings.
unique_variants = sorted(
    unique_variants,
    key=len,
    reverse=True
)[:3]

if not unique_variants:
    unique_variants = [social_claim]

variants = [
    {
        "id": f"V{i}",
        "claim": text
    }
    for i, text in enumerate(
        unique_variants,
        1
    )
]


# =========================================================
# 5. SCIENTIFIC EVIDENCE VERDICT
# =========================================================

paper_context = []

for index, paper in enumerate(
    top_papers,
    1
):
    paper_context.append(
        f"""
PAPER {index}
PMID: {paper.get('pmid')}
Title: {paper.get('title')}
Year: {paper.get('year')}
Abstract:
{paper.get('abstract', '')}
"""
    )

evidence_prompt = f"""
You are evaluating scientific evidence relative to a
specific health narrative.

HEALTH CLAIM:
{canonical_claim}

RETRIEVED PAPERS:
{''.join(paper_context)}

Use ONLY the supplied papers.

Choose one evidence verdict:

SUPPORTED
- the supplied evidence directly supports the central claim

MIXED
- the evidence supports some components but not the complete
  proposition, or findings meaningfully differ across studies

REFUTED
- the supplied evidence directly contradicts the central claim

INSUFFICIENT
- the supplied evidence does not directly establish or
  directly refute the claim

Be conservative.
A related paper is not automatically evidence.
Observational association alone does not establish causation.

Return ONLY valid JSON:

{{
  "verdict": "SUPPORTED|MIXED|REFUTED|INSUFFICIENT",
  "summary": "2-4 sentence evidence-grounded summary",
  "paper_assessments": [
    {{
      "pmid": "PMID or null",
      "relationship": "SUPPORTS|CONTRADICTS|PARTIAL|RELATED_ONLY",
      "finding": "brief finding",
      "limitation": "brief limitation relative to claim"
    }}
  ]
}}
"""

try:
    evidence_result = extract_json(
        generate_text(
            evidence_prompt,
            primary=primary_model,
            max_tokens=1400
        )
    )

except Exception as error:
    print(
        "Evidence reasoning fallback:",
        str(error)[:160]
    )

    evidence_result = {
        "verdict": "INSUFFICIENT",
        "summary": (
            "Automated evidence reasoning could not be "
            "completed reliably for this run."
        ),
        "paper_assessments": []
    }


verdict = str(
    evidence_result.get(
        "verdict",
        "INSUFFICIENT"
    )
).upper()

if verdict not in {
    "SUPPORTED",
    "MIXED",
    "REFUTED",
    "INSUFFICIENT"
}:
    verdict = "INSUFFICIENT"


assessment_by_pmid = {
    str(item.get("pmid")): item
    for item in evidence_result.get(
        "paper_assessments",
        []
    )
    if item.get("pmid")
}

sources = []

for paper in top_papers:

    pmid = paper.get("pmid")

    assessment = assessment_by_pmid.get(
        str(pmid),
        {}
    )

    sources.append({
        "pmid": pmid,
        "title": paper.get("title"),
        "year": paper.get("year"),
        "journal": paper.get("journal"),
        "semantic_relevance": paper.get(
            "semantic_relevance"
        ),
        "relationship": assessment.get(
            "relationship",
            "RELATED_ONLY"
        ),
        "finding": assessment.get(
            "finding",
            ""
        ),
        "limitation": assessment.get(
            "limitation",
            ""
        )
    })


# =========================================================
# 6. MED MAPPING
# =========================================================

MED_MAP = {
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

med = MED_MAP[verdict]

for variant in variants:
    variant["evidence_alignment"] = (
        med["alignment"]
    )


# =========================================================
# 7. SEMANTIC MUTATION
# =========================================================

semantic_mutations = []

if len(variants) >= 2:

    variant_embeddings = embedder.encode(
        [v["claim"] for v in variants],
        normalize_embeddings=True,
        show_progress_bar=False
    )

    for i in range(
        len(variants) - 1
    ):

        similarity = float(
            np.dot(
                variant_embeddings[i],
                variant_embeddings[i + 1]
            )
        )

        distance = 1.0 - similarity

        semantic_mutations.append({
            "from": variants[i]["id"],
            "to": variants[i + 1]["id"],
            "cosine_similarity": round(
                similarity,
                3
            ),
            "distance": round(
                distance,
                3
            )
        })


mutation_status = (
    "OBSERVED_VARIATION"
    if len(variants) >= 2
    else "NO_OBSERVED_VARIATION"
)


# =========================================================
# 8. BEHAVIOR SIGNAL
# =========================================================

behavior_patterns = [
    r"\bshould\b",
    r"\bmust\b",
    r"\bavoid\b",
    r"\bstop taking\b",
    r"\bstop using\b",
    r"\bdon't take\b",
    r"\bdo not take\b",
    r"\btry\b",
    r"\baim for\b",
    r"\brecommend\b",
    r"\bstart taking\b",
    r"\bget vaccinated\b",
    r"\bdon't get\b",
    r"\bdo not get\b"
]

behavior_details = []

for post in posts:

    text = clean_text(
        post.get("text", "")
    )

    lower = text.lower()

    if any(
        re.search(pattern, lower)
        for pattern in behavior_patterns
    ):
        behavior_details.append({
            "id": post.get("id"),
            "text": text
        })

behavior_posts = len(
    behavior_details
)

observed_posts = int(
    narrative.get(
        "observed_posts",
        len(posts)
    )
    or 0
)

behavior_rate = (
    behavior_posts / observed_posts
    if observed_posts
    else 0.0
)


# =========================================================
# 9. PRIORITY
# =========================================================

maturity = (
    "REPEATED_MEME"
    if observed_posts >= 2
    and int(
        narrative.get(
            "unique_authors",
            0
        )
        or 0
    ) >= 2
    else "EMERGING_CLAIM"
)

behavior_detected = (
    behavior_posts > 0
)

if verdict == "SUPPORTED":

    priority_flag = "🟢"
    priority_label = "EVIDENCE_ALIGNED"
    priority_rationale = (
        "The retrieved evidence is aligned with the "
        "central health proposition."
    )

elif (
    verdict == "REFUTED"
    and maturity == "REPEATED_MEME"
    and behavior_detected
):

    priority_flag = "🚨"
    priority_label = (
        "PRIORITY_HARMFUL_NARRATIVE"
    )
    priority_rationale = (
        "The narrative shows high evidence divergence, "
        "repeated transmission, and explicit behavioral "
        "activation."
    )

elif (
    med["divergence"] == "MODERATE"
    and behavior_detected
):

    priority_flag = "🟠"
    priority_label = (
        "BEHAVIOR_ACTIVE_WATCH"
    )
    priority_rationale = (
        "The narrative has moderate evidence divergence "
        "and explicit behavioral activation."
    )

else:

    priority_flag = "👀"
    priority_label = "WATCH"

    if verdict == "INSUFFICIENT":
        priority_rationale = (
            "Scientific evidence is currently unresolved "
            "for the central proposition."
        )
    else:
        priority_rationale = (
            "The narrative warrants monitoring based on "
            "its evidence relationship and observed "
            "cultural transmission, but the current "
            "behavior criteria for escalation were not met."
        )


# =========================================================
# 10. DIFFUSION
# =========================================================

times = []

for post in posts:
    value = post.get("created_at")

    if value:
        try:
            from datetime import datetime
            times.append(
                datetime.fromisoformat(
                    value
                )
            )
        except Exception:
            pass

first_seen = (
    min(times).isoformat()
    if times else None
)

last_seen = (
    max(times).isoformat()
    if times else None
)

if len(times) >= 2:
    persistence_minutes = (
        max(times) - min(times)
    ).total_seconds() / 60
else:
    persistence_minutes = 0

hours = (
    persistence_minutes / 60
)

posts_per_hour = (
    observed_posts / hours
    if hours > 0
    else None
)


# =========================================================
# 11. SAVE CACHE
# =========================================================

cache_id = slugify(
    canonical_claim
)

cache = {
    "cache_id": cache_id,
    "analysis_type": "DEEP_ANALYSIS",
    "title": canonical_claim,
    "canonical_claim": canonical_claim,

    "match_terms": build_match_terms(
        social_claim
    ),

    "analysis_provider": primary_model,

    "diffusion": {
        "observed_posts": observed_posts,
        "unique_participants": int(
            narrative.get(
                "unique_authors",
                0
            )
            or 0
        ),
        "posts_per_hour": (
            round(posts_per_hour, 2)
            if posts_per_hour is not None
            else None
        ),
        "max_observed_reposts": int(
            narrative.get(
                "max_retweets",
                0
            )
            or 0
        ),
        "first_seen": first_seen,
        "last_seen": last_seen,
        "persistence_minutes": round(
            persistence_minutes,
            2
        )
    },

    "meme_dna": {
        "mutation_status": mutation_status,
        "distinct_variants": len(variants),
        "variants": variants,
        "semantic_mutations": (
            semantic_mutations
        )
    },

    "evidence": {
        "verdict": verdict,
        "summary": evidence_result.get(
            "summary",
            ""
        ),
        "sources": sources
    },

    "divergence": {
        "alignment": med["alignment"],
        "overall_level": (
            med["divergence"]
        ),
        "largest_divergence": (
            variants[-1]["id"]
            if variants else "Narrative"
        ),
        "baseline": evidence_result.get(
            "summary",
            ""
        ),
        "interpretation": (
            f"The narrative was compared with the "
            f"retrieved scientific evidence. "
            f"Overall evidence alignment is "
            f"{med['alignment']} and Meme–Evidence "
            f"Divergence is {med['divergence']}."
        )
    },

    "behavior": {
        "signal_posts": behavior_posts,
        "analyzed_posts": observed_posts,
        "rate": round(
            behavior_rate,
            4
        ),
        "detected": behavior_detected,
        "posts": behavior_details[:10]
    },

    "priority": {
        "flag": priority_flag,
        "label": priority_label,
        "rationale": priority_rationale
    },

    "method_note": (
        "Fresh Deep Analysis combines semantic "
        "narrative variation, scientific-literature "
        "retrieval, evidence evaluation, "
        "Meme–Evidence Divergence, and explicit "
        "behavioral-intention detection."
    )
}

output = (
    CACHE_DIR
    / f"{cache_id}.json"
)

with open(output, "w") as f:
    json.dump(
        cache,
        f,
        indent=2,
        ensure_ascii=False
    )

print("\nDEEP ANALYSIS COMPLETE")
print("Cache:", output)
print("Provider preference:", primary_model)
print("Canonical claim:", canonical_claim)
print("Evidence verdict:", verdict)
print(
    "Meme–Evidence Divergence:",
    med["divergence"]
)
print(
    "Variants:",
    len(variants)
)
print(
    "Behavior rate:",
    f"{behavior_rate * 100:.1f}%"
)
print(
    "Priority:",
    priority_flag,
    priority_label
)
