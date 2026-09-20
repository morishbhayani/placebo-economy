import json
import streamlit as st
from prioritization import prioritize

st.set_page_config(
    page_title="Placebo Economy",
    page_icon="🧬",
    layout="wide"
)

with open("evidence_profile.json") as f:
    evidence = json.load(f)

with open("meme_evidence_divergence.json") as f:
    med = json.load(f)

with open("cultural_metrics.json") as f:
    cultural = json.load(f)

st.title("Placebo Economy")
st.caption(
    "Tracking how health narratives spread, mutate, diverge from evidence, "
    "and begin influencing behavior."
)

st.divider()

st.subheader("Narrative under observation")
st.markdown(f"### {evidence['claim']}")

st.caption(
    "This is the canonical health narrative currently being analyzed."
)

st.divider()

# CULTURAL SIGNALS
st.subheader("1. Cultural diffusion")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Observed claim posts",
    cultural["observed_claim_posts"]
)

c2.metric(
    "Unique participants",
    cultural["unique_participants"]
)

c3.metric(
    "Posts / hour",
    cultural["posts_per_hour"]
)

c4.metric(
    "Max observed reposts",
    f"{cultural['max_observed_reposts']:,}"
)

st.caption(
    "Metrics reflect the analyzed Calcifer dataset window, not global X activity."
)

# Diffusion timeline
import pandas as pd

timeline = pd.read_csv("diffusion_timeline.csv")
timeline["time_bucket"] = pd.to_datetime(timeline["time_bucket"])

timeline["time"] = timeline["time_bucket"].dt.strftime("%I:%M %p")

st.markdown("#### Claim activity — August 16, 2026")

st.bar_chart(
    timeline,
    x="time",
    y="posts"
)

st.caption(
    "Each bar shows the number of posts promoting this claim observed "
    "during that 10-minute interval in the Calcifer sample."
)

st.divider()

# MEME DNA
st.subheader("2. Meme DNA")

st.write(
    "This map shows different observed versions of the same underlying "
    "health narrative and how their meaning differs."
)

st.graphviz_chart("""
digraph MemeDNA {

    rankdir=LR;

    node [
        shape=box,
        style="rounded,filled",
        fontname="Arial",
        fontsize=12,
        margin=0.18
    ];

    V1 [
        label="V1\\nPfizer mRNA vaccine\\ninduces 'turbo cancer'\\n\\nEvidence alignment: LOW"
    ];

    V2 [
        label="V2\\nCOVID vaccines raise risk\\nof multiple cancers\\n\\nEvidence alignment: PARTIAL"
    ];

    V3 [
        label="V3\\nmRNA vaccines cause turbo cancer\\nand are purely harmful\\n\\nEvidence alignment: VERY LOW"
    ];

    V1 -> V2 [
        label="semantic distance 0.422"
    ];

    V2 -> V3 [
        label="semantic distance 0.528"
    ];
}
""", use_container_width=True)

st.caption(
    "These are observed related variants in the dataset, not proof that "
    "V1 literally evolved into V2 and then V3."
)

st.info(
    "The biggest semantic difference is between V2 and V3. "
    "V3 adds much stronger causal and universal-harm language."
)

st.divider()

# LOCAL LLM ANALYSIS
st.subheader("3. Local LLM interpretation")

with open("llm_analysis.json") as f:
    llm_data = json.load(f)

st.caption(
    f"Semantic interpretation generated locally with {llm_data['model']} "
    "and validated with deterministic guardrails."
)

llm_rows = []

for v in llm_data["variants"]:
    llm_rows.append({
        "Variant": f"Variant {v['variant_number']}",
        "Observed": v["observed_count"],
        "Stance": v["stance"],
        "Normalized claim": v["normalized_claim"],
        "Behavior": v["behavior"]
    })

llm_df = pd.DataFrame(llm_rows)

c1, c2, c3 = st.columns(3)

c1.metric(
    "Claims detected",
    int((llm_df["Stance"] == "CLAIM").sum())
)

c2.metric(
    "Counter-claims detected",
    int((llm_df["Stance"] == "COUNTER_CLAIM").sum())
)

c3.metric(
    "Explicit behavior signals",
    int((llm_df["Behavior"] != "NONE").sum())
)

st.dataframe(
    llm_df,
    use_container_width=True,
    hide_index=True
)

with st.expander("How the AI layer works"):
    st.write(
        "The local LLM converts messy social-media language into structured "
        "claims and stance labels. Deterministic rules then validate fields "
        "such as behavioral intention so unsupported model outputs do not "
        "automatically enter the analysis."
    )

st.divider()

# EVIDENCE
st.subheader("4. Scientific evidence")

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

        pmid = source["pmid"]
        pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

        st.markdown(
            f"**[{source['study_type']} · {source['year']} · PMID {pmid}]"
            f"({pubmed_url})**"
        )

        st.write("**Finding:**", source["finding"])
        st.write("**Limitation:**", source["limitation"])

        st.markdown("---")

st.divider()

# DIVERGENCE
st.subheader("5. Meme–Evidence Divergence")

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

st.markdown("#### Evidence divergence map")

st.graphviz_chart("""
digraph Divergence {

    rankdir=TB;

    node [
        shape=box,
        style="rounded,filled",
        fontname="Arial",
        fontsize=11,
        margin=0.18
    ];

    E [
        label="SCIENTIFIC EVIDENCE BASELINE\\n\\nObservational signals exist,\\nbut causation is not established"
    ];

    V1 [
        label="V1\\nVaccine induces 'turbo cancer'"
    ];

    V2 [
        label="V2\\nVaccines raise risk\\nof multiple cancers"
    ];

    V3 [
        label="V3\\nVaccines cause turbo cancer\\n+ purely harmful / zero benefit"
    ];

    V1 -> E [label="LOW alignment"];
    V2 -> E [label="PARTIAL alignment"];
    V3 -> E [label="VERY LOW alignment"];
}
""", use_container_width=True)

st.caption(
    "The evidence baseline stays fixed. The visualization shows how closely "
    "each observed narrative variant matches what the retrieved evidence supports."
)

st.divider()

# BEHAVIOR
st.subheader("6. Belief → behavior")

b1, b2 = st.columns(2)

# Weight behavior by how many times each distinct variant was observed
total_behavior_posts = sum(
    int(v["observed_count"])
    for v in llm_data["variants"]
)

behavior_signal_posts = sum(
    int(v["observed_count"])
    for v in llm_data["variants"]
    if v["behavior"] != "NONE"
)

behavior_rate = (
    (behavior_signal_posts / total_behavior_posts) * 100
    if total_behavior_posts else 0
)

b1.metric(
    "Explicit behavior signals",
    f"{behavior_signal_posts} / {total_behavior_posts}"
)

b2.metric(
    "Behavioral intention rate",
    f"{behavior_rate:.2f}%"
)

if behavior_signal_posts == 0:
    st.caption(
        "No explicit behavioral intention was detected in the analyzed "
        "vaccine+cancer posts."
    )
else:
    st.caption(
        "At least one analyzed post contained an explicit behavioral signal."
    )

st.divider()

# PRIORITIZATION
st.subheader("7. Public-health prioritization")

# Derive prioritization inputs from actual analysis outputs

# Evidence is considered aligned only when our evidence engine
# explicitly reports support.
evidence_aligned = evidence["verdict"] == "SUPPORTED"

# Total observed claim posts from the real diffusion timeline
observed_claim_posts = int(timeline["posts"].sum())

# MVP rule: repeated activity in at least 5 observed posts
# counts as meaningful momentum within this sample.
observed_momentum = observed_claim_posts >= 5

# Behavior comes from the validated local-LLM output
behavioral_intent_detected = bool(
    (llm_df["Behavior"] != "NONE").any()
)

priority = prioritize(
    evidence_aligned=evidence_aligned,
    observed_momentum=observed_momentum,
    behavioral_intent_detected=behavioral_intent_detected
)

icons = {
    "HEALTHY_DIFFUSION": "🟢",
    "CULTURALLY_OVERLOOKED": "💎",
    "WATCH": "👀",
    "PRIORITY_SIGNAL": "🚨",
    "MONITOR": "⚪"
}

icon = icons.get(priority["category"], "⚪")

st.markdown(f"### {icon} {priority['label'].upper()}")
st.write(priority["reason"])

p1, p2, p3 = st.columns(3)

p1.metric(
    "Evidence alignment",
    "DIVERGENT" if not evidence_aligned else "ALIGNED"
)

p2.metric(
    "Observed spread",
    "YES" if observed_momentum else "LIMITED"
)

p3.metric(
    "Behavior signal",
    "YES" if behavioral_intent_detected else "NO"
)

st.caption(
    "Placebo Economy separates cultural spread, scientific evidence, "
    "semantic mutation, and behavioral activation instead of collapsing "
    "them into a single opaque score."
)
