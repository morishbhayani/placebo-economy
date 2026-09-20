import json
import re
import html
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"

with open("ranked_narrative_evidence.json") as f:
    evidence_sets = json.load(f)

def clean(text):
    text = html.unescape(str(text or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

outputs = []

print("\nEVIDENCE VERDICTS\n")

for narrative in evidence_sets:

    claim = narrative["claim"]
    papers = narrative["papers"][:3]

    evidence_text = ""

    for i, paper in enumerate(papers, 1):
        evidence_text += f"""
PAPER {i}
TITLE: {clean(paper["title"])}
YEAR: {paper.get("year", "")}
PMID: {paper.get("pmid", "")}
ABSTRACT:
{clean(paper.get("abstract", ""))}
"""

    prompt = f"""
You are evaluating scientific evidence relative to a health narrative.

HEALTH NARRATIVE:
{claim}

Use ONLY the supplied paper titles and abstracts.

Possible overall verdicts:

SUPPORTED
- the retrieved evidence directly and consistently supports the major
  components of the narrative

MIXED
- some important components are supported, but other components are
  unsupported, uncertain, conflicting, or overstated

REFUTED
- the supplied evidence directly contradicts the central narrative

INSUFFICIENT
- the supplied evidence does not directly establish the narrative

STRICT RULES:

1. Association is not causation.
2. Do not infer beyond the supplied abstracts.
3. If the narrative contains several outcomes, do not mark SUPPORTED unless
   the major components are actually addressed.
4. A paper about a related topic is not automatically evidence for the claim.
5. Population differences and study-design limitations matter.
6. Do not treat absence of evidence as evidence of absence.
7. Do not judge the social-media author; evaluate only the proposition.
8. Be conservative.

For each paper classify its relationship to the narrative as:
SUPPORTS
PARTIAL
CONTRADICTS
UNCLEAR

Return JSON only:

{{
  "verdict": "MIXED",
  "summary": "2-3 sentence evidence-grounded summary",
  "papers": [
    {{
      "paper": 1,
      "relationship": "PARTIAL",
      "finding": "brief description based only on abstract",
      "limitation": "brief limitation relative to this narrative"
    }}
  ]
}}

EVIDENCE:
{evidence_text}
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
        result = json.loads(r.json()["response"])

    except Exception as e:
        print("Failed:", claim, e)
        continue

    verdict = str(result.get("verdict", "INSUFFICIENT")).upper()

    if verdict not in {
        "SUPPORTED",
        "MIXED",
        "REFUTED",
        "INSUFFICIENT"
    }:
        verdict = "INSUFFICIENT"

    record = {
        "rank": narrative["rank"],
        "claim": claim,
        "verdict": verdict,
        "summary": result.get("summary", ""),
        "papers": result.get("papers", []),
        "sources": [
            {
                "title": p["title"],
                "pmid": p.get("pmid"),
                "year": p.get("year"),
                "semantic_relevance": p.get("semantic_relevance")
            }
            for p in papers
        ]
    }

    outputs.append(record)

    print("=" * 90)
    print(f"NARRATIVE {narrative['rank']}")
    print("Claim:", claim)
    print("Verdict:", verdict)
    print("Summary:", record["summary"])

    for p in record["papers"]:
        print(
            f"Paper {p.get('paper')}: "
            f"{p.get('relationship')}"
        )
        print(" Finding:", p.get("finding"))
        print(" Limitation:", p.get("limitation"))

    print()

with open("narrative_evidence_verdicts.json", "w") as f:
    json.dump(outputs, f, indent=2)

print("Saved to narrative_evidence_verdicts.json")
