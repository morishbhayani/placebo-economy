import json
import requests
import re
import html

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"

with open("data/processed/narrative_evidence_candidates.json") as f:
    evidence_sets = json.load(f)

def clean(text):
    text = html.unescape(str(text or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("’", "'").replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def normalize(text):
    text = clean(text).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

filtered_all = []

print("\nEVIDENCE RELEVANCE FILTER\n")

for narrative in evidence_sets:

    rank = narrative["rank"]
    claim = narrative["claim"]

    papers = [
        p for p in narrative["candidate_papers"]
        if clean(p.get("abstract", ""))
    ][:10]

    paper_blocks = []

    for i, p in enumerate(papers):
        paper_blocks.append(
            f"""
PAPER {i}
TITLE: {clean(p['title'])}
ABSTRACT: {clean(p['abstract'])}
"""
        )

    prompt = f"""
Screen scientific papers for relevance to this health narrative.

NARRATIVE:
{claim}

Classification:

DIRECT:
The paper directly examines substantially the same exposure/intervention
and substantially the same outcome.

PARTIAL:
The paper directly examines an important component of the narrative,
but not the entire claim.

IRRELEVANT:
It only shares broad topic words or examines a materially different question.

Important:
- A narrative may contain multiple outcomes. A paper studying one of those
  outcomes can be PARTIAL.
- Do not decide yet whether the narrative is scientifically true.
- Do not invent findings.
- For DIRECT or PARTIAL, copy one short phrase VERBATIM from the title
  or abstract that demonstrates relevance.
- Be conservative about DIRECT.

Return JSON only:

{{
  "papers": [
    {{
      "paper": 0,
      "relevance": "DIRECT",
      "evidence_quote": "verbatim phrase"
    }}
  ]
}}

PAPERS:
{"".join(paper_blocks)}
"""

    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0}
            },
            timeout=240
        )

        r.raise_for_status()
        response = json.loads(r.json()["response"])

    except Exception as e:
        print(f"Narrative {rank} failed:", e)
        continue

    selected = []

    for result in response.get("papers", []):

        idx = result.get("paper")
        relevance = str(result.get("relevance", "")).upper()
        quote = clean(result.get("evidence_quote", ""))

        if (
            not isinstance(idx, int)
            or not 0 <= idx < len(papers)
            or relevance not in {"DIRECT", "PARTIAL"}
            or not quote
        ):
            continue

        paper = papers[idx]

        source = normalize(
            paper["title"] + " " + paper["abstract"]
        )

        grounded_quote = normalize(quote)

        # Grounding still required, but after removing
        # HTML/punctuation/whitespace differences.
        if grounded_quote not in source:
            continue

        selected.append({
            **paper,
            "relevance": relevance,
            "evidence_quote": quote
        })

    selected.sort(
        key=lambda p: (
            p["relevance"] == "DIRECT",
            bool(p["abstract"]),
            p["cited_by_count"]
        ),
        reverse=True
    )

    selected = selected[:5]

    filtered_all.append({
        "rank": rank,
        "claim": claim,
        "relevant_papers": selected
    })

    print("=" * 90)
    print(f"NARRATIVE {rank}")
    print("Claim:", claim)
    print("Relevant papers retained:", len(selected))

    for i, p in enumerate(selected, 1):
        print(
            f"{i}. {p['relevance']} "
            f"[{p['year']}] {p['title']}"
        )
        if p["pmid"]:
            print("   PMID:", p["pmid"])
        print("   Grounding:", p["evidence_quote"])
        print()

with open("data/processed/filtered_narrative_evidence.json", "w") as f:
    json.dump(filtered_all, f, indent=2)

print("Saved to filtered_narrative_evidence.json")
