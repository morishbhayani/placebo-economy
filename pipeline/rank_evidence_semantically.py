import json
import re
import html
import numpy as np
from sentence_transformers import SentenceTransformer

with open("data/processed/narrative_evidence_candidates.json") as f:
    evidence_sets = json.load(f)

def clean(text):
    text = html.unescape(str(text or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

model = SentenceTransformer("all-MiniLM-L6-v2")

ranked_all = []

print("\nSEMANTIC EVIDENCE RANKING\n")

for narrative in evidence_sets:

    claim = clean(narrative["claim"])

    papers = [
        p for p in narrative["candidate_papers"]
        if clean(p.get("abstract"))
    ]

    if not papers:
        ranked_all.append({
            "rank": narrative["rank"],
            "claim": claim,
            "papers": []
        })
        continue

    documents = [
        clean(p["title"]) + ". " + clean(p["abstract"])
        for p in papers
    ]

    claim_embedding = model.encode(
        [claim],
        normalize_embeddings=True
    )[0]

    paper_embeddings = model.encode(
        documents,
        normalize_embeddings=True,
        show_progress_bar=False
    )

    similarities = np.dot(
        paper_embeddings,
        claim_embedding
    )

    ranked_indices = np.argsort(similarities)[::-1]

    ranked_papers = []

    for idx in ranked_indices[:5]:

        paper = dict(papers[idx])
        paper["semantic_relevance"] = round(
            float(similarities[idx]), 3
        )

        ranked_papers.append(paper)

    ranked_all.append({
        "rank": narrative["rank"],
        "claim": claim,
        "papers": ranked_papers
    })

    print("=" * 90)
    print(f"NARRATIVE {narrative['rank']}")
    print("Claim:", claim)

    for i, paper in enumerate(ranked_papers, 1):

        print(
            f"{i}. similarity={paper['semantic_relevance']:.3f}"
        )
        print("   TITLE:", clean(paper["title"]))

        if paper.get("pmid"):
            print("   PMID:", paper["pmid"])

        print()


with open("data/processed/ranked_narrative_evidence.json", "w") as f:
    json.dump(ranked_all, f, indent=2)

print("Saved to ranked_narrative_evidence.json")
