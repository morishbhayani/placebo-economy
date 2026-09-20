import json
import requests
import re

EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

with open("top_narratives.json") as f:
    narratives = json.load(f)


def build_queries(claim):
    """
    Focused scientific retrieval for the canonical health proposition:
    DTP vaccination causes autism.
    """

    return [
        '"diphtheria tetanus pertussis" autism',
        '"DTP vaccine" autism',
        '"pertussis vaccine" autism',
        'vaccination autism systematic review',
        'vaccines autism cohort study'
    ]


all_evidence = []

print("\nSCIENTIFIC EVIDENCE RETRIEVAL\n")

for rank, narrative in enumerate(narratives, 1):

    claim = narrative["claim"]

    queries = build_queries(claim)

    papers = {}

    print("=" * 90)
    print(f"NARRATIVE {rank}")
    print("Claim:", claim)
    print("Queries:", queries)

    for query in queries:

        params = {
            "query": query,
            "format": "json",
            "resultType": "core",
            "pageSize": 15
        }

        try:
            r = requests.get(
                EUROPE_PMC,
                params=params,
                timeout=30
            )

            r.raise_for_status()

            results = (
                r.json()
                .get("resultList", {})
                .get("result", [])
            )

        except Exception as e:
            print("Search error:", query, e)
            continue

        for paper in results:

            pmid = paper.get("pmid")
            pmcid = paper.get("pmcid")

            key = (
                pmid
                or pmcid
                or paper.get("id")
                or paper.get("title")
            )

            if not key:
                continue

            papers[key] = {
                "pmid": pmid,
                "pmcid": pmcid,
                "title": paper.get("title", ""),
                "authors": paper.get("authorString", ""),
                "journal": paper.get("journalTitle", ""),
                "year": paper.get("pubYear", ""),
                "publication_type": paper.get(
                    "pubTypeList", {}
                ).get("pubType", []),
                "cited_by_count": int(
                    paper.get("citedByCount", 0) or 0
                ),
                "abstract": paper.get(
                    "abstractText", ""
                ),
                "search_query": query
            }

    papers = list(papers.values())

    papers.sort(
        key=lambda p: (
            bool(p["abstract"]),
            p["cited_by_count"]
        ),
        reverse=True
    )

    papers = papers[:15]

    all_evidence.append({
        "rank": rank,
        "claim": claim,
        "queries": queries,
        "candidate_papers": papers
    })

    print("Candidate papers:", len(papers))

    for i, paper in enumerate(papers[:5], 1):
        print(
            f"{i}. [{paper['year']}] "
            f"{paper['title']}"
        )

        if paper["pmid"]:
            print("   PMID:", paper["pmid"])

    print()


with open("narrative_evidence_candidates.json", "w") as f:
    json.dump(all_evidence, f, indent=2)

print("Saved to narrative_evidence_candidates.json")
