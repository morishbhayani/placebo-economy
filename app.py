import json
import streamlit as st

st.set_page_config(
    page_title="Placebo Economy",
    page_icon="🧬",
    layout="wide"
)

with open("evidence_profile.json") as f:
    evidence = json.load(f)

with open("meme_evidence_divergence.json") as f:
    med = json.load(f)

st.title("Placebo Economy")
st.caption(
    "Tracking how health narratives spread, mutate, diverge from evidence, "
    "and begin influencing behavior."
)

st.divider()

st.subheader("Narrative under observation")
st.markdown("### COVID-19 mRNA vaccines cause “turbo cancer”")

st.warning(
    "WATCH — Evidence divergence is present, but explicit behavioral "
    "activation was not detected in the analyzed sample."
)

st.divider()

# CULTURAL SIGNALS
st.subheader("1. Cultural diffusion")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Observed claim posts", "12")
c2.metric("Unique participants", "12")
c3.metric("Posts / hour", "10.29")
c4.metric("Max observed reposts", "3,553")

st.caption(
    "Metrics reflect the analyzed Calcifer dataset window, not global X activity."
)

st.divider()

# MEME DNA
st.subheader("2. Meme DNA")

variants = med["variants"]

for i, v in enumerate(variants):
    st.markdown(f"**{v['variant_id']} — {v['evidence_alignment']} evidence alignment**")
    st.write(v["claim"])
    st.caption(v["reason"])

    if i < len(variants) - 1:
        st.markdown("↓")

st.info(
    "Semantic mutation: V1 → V2 = 0.422 | V2 → V3 = 0.528"
)

st.caption(
    "These are observed variants in the sample, not a proven chronological lineage."
)

st.divider()

# EVIDENCE
st.subheader("3. Scientific evidence")

st.markdown(
    f"### Verdict: {evidence['verdict'].replace('_', ' ')}"
)

st.write(evidence["summary"])

a, b, c, d = st.columns(4)

a.metric(
    "Population cohorts",
    evidence["evidence_availability"]["direct_population_cohorts"]
)

b.metric(
    "Literature reviews",
    evidence["evidence_availability"]["literature_reviews"]
)

c.metric(
    "Method critiques",
    evidence["evidence_availability"]["methodological_critiques"]
)

d.metric(
    "Commentaries",
    evidence["evidence_availability"]["commentaries"]
)

with st.expander("View evidence sources"):
    for source in evidence["sources"]:
        st.markdown(
            f"**PMID {source['pmid']} · {source['year']} · "
            f"{source['study_type']}**"
        )
        st.write(source["finding"])
        st.caption("Limitation: " + source["limitation"])
        st.markdown("---")

st.divider()

# DIVERGENCE
st.subheader("4. Meme–Evidence Divergence")

st.write(med["evidence_baseline"])

st.markdown(
    "**Observed divergence pattern:** "
    "V1 → V2: closer to evidence · "
    "V2 → V3: strongly away from evidence"
)

st.error(
    "Largest divergence: V3 — categorical causation and universal-harm "
    "language substantially exceed the retrieved evidence."
)

st.write(med["interpretation"])

st.divider()

# BEHAVIOR
st.subheader("5. Belief → behavior")

b1, b2 = st.columns(2)

b1.metric("Explicit behavior signals", "0 / 20")
b2.metric("Behavioral intention rate", "0.00%")

st.caption(
    "No explicit avoid/refuse/stop/recommend-against behavior was detected "
    "in the analyzed vaccine+cancer posts."
)

st.divider()

# PRIORITIZATION
st.subheader("6. Public-health prioritization")

st.markdown("### 👀 WATCH")

st.write(
    "The narrative shows observed cultural momentum and evidence divergence, "
    "but no explicit behavioral activation was detected in this sample."
)

st.caption(
    "Placebo Economy separates cultural spread, scientific evidence, "
    "semantic mutation, and behavioral activation instead of collapsing "
    "them into a single opaque score."
)
