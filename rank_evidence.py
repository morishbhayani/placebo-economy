import requests
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

CLAIM = "COVID-19 mRNA vaccines cause rapidly developing or aggressive cancers, sometimes called turbo cancer."

url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

queries = [
    '"COVID-19 vaccine" AND ("turbo cancer" OR "cancer risk" OR "cancer incidence")',
    '("COVID-19 vaccine" OR "mRNA COVID-19 vaccine") AND (cancer OR malignancy OR neoplasm) AND (risk OR incidence OR safety)'
]

papers = {}

for query in queries:
    params = {
        "query": query,
        "format": "json",
        "resultType": "core",
        "pageSize": 30
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()

    for p in r.json()["resultList"]["result"]:
        pmid = p.get("pmid")
        title = p.get("title", "")
        abstract = p.get("abstractText", "")

        if not title or not abstract:
            continue

        key = pmid or title

        papers[key] = {
            "pmid": pmid,
            "title": title,
            "year": p.get("pubYear"),
            "abstract": abstract
        }

model = SentenceTransformer("all-MiniLM-L6-v2")

claim_embedding = model.encode([CLAIM])

for paper in papers.values():
    text = paper["title"] + ". " + paper["abstract"]
    paper_embedding = model.encode([text])

    similarity = cosine_similarity(
        claim_embedding,
        paper_embedding
    )[0][0]

    paper["relevance"] = float(similarity)

ranked = sorted(
    papers.values(),
    key=lambda x: x["relevance"],
    reverse=True
)

print("\nTOP EVIDENCE CANDIDATES\n")

for i, p in enumerate(ranked[:10], 1):
    print(f"--- {i} ---")
    print(f"Relevance: {p['relevance']:.3f}")
    print("Title:", p["title"])
    print("Year:", p["year"])
    print("PMID:", p["pmid"])
    print()
