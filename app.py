import json
import sys
import subprocess
from pathlib import Path
import textwrap
import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(
    page_title="Epi Meme Ology",
    page_icon="🧬",
    layout="wide"
)

with open("data/runtime/dashboard_payload.json") as f:
    data = json.load(f)

fast_mode = data.get("mode") == "FAST_SCAN"

# ---------------------------------------------------------
# CACHED DEEP ANALYSIS
# ---------------------------------------------------------

deep_caches = []

for cache_path in Path("data/deep_cache").glob("*.json"):
    try:
        with open(cache_path) as f:
            cache = json.load(f)

        cache["_path"] = str(cache_path)
        deep_caches.append(cache)

    except Exception:
        pass


def find_deep_cache(text):
    text_lower = text.lower()

    best = None
    best_score = 0

    for cache in deep_caches:

        terms = [
            str(term).lower()
            for term in cache.get("match_terms", [])
        ]

        matched = [
            term
            for term in terms
            if term in text_lower
        ]

        has_specific_phrase = any(
            " " in term and term in text_lower
            for term in terms
        )

        score = len(matched)

        if (
            score >= 3
            and has_specific_phrase
            and score > best_score
        ):
            best = cache
            best_score = score

    return best


st.title("Epi Meme Ology")

st.caption(
    "Discovering how health narratives spread, replicate or mutate, "
    "diverge from scientific evidence, and begin influencing behavior."
)

if fast_mode:
    st.info(
        "⚡ FAST SCAN — This mode detects and ranks recurring health "
        "narratives from the observed social dataset. Scientific evidence, "
        "Meme–Evidence Divergence, behavioral activation, and public-health "
        "risk are not evaluated in Fast Scan."
    )

st.divider()

# ---------------------------------------------------------
# SEARCH / OBSERVATION CONTEXT
# ---------------------------------------------------------

st.subheader("Health narrative discovery")

keyword = st.text_input(
    "Healthcare keyword",
    value=data["keyword"],
    help=(
        "Enter a healthcare topic such as sleep, vaccine, caffeine, "
        "melatonin, anxiety, or magnesium."
    )
)


selected_model = st.selectbox(
    "AI reasoning model",
    [
        "Gemini",
        "Groq",
        "Ollama"
    ],
    help=(
        "Your selection is used first. "
        "The other models are automatic fallbacks."
    )
)

analyze_clicked = st.button(
    "Analyze keyword",
    type="primary"
)

if analyze_clicked:

    search_term = keyword.strip()

    if not search_term:
        st.error("Enter a healthcare keyword first.")

    else:
        with st.spinner(
            f"Scanning '{search_term}' for recurring health narratives..."
        ):

            result = subprocess.run(
                [
                    sys.executable,
                    "run_fast_scan.py",
                    search_term
                ],
                capture_output=True,
                text=True
            )

        if result.returncode == 0:
            st.success(
                f"Analysis complete for '{search_term}'. "
                "Loading the new narratives..."
            )
            st.rerun()

        else:
            st.error(
                "The analysis pipeline stopped before completion."
            )

            with st.expander("Show pipeline error"):
                st.code(
                    result.stdout + "\n" + result.stderr
                )

window = data["observation_window"]

st.caption(
    f"Current analyzed keyword: **{data['keyword']}** · "
    f"Observation window: {window['first']} → {window['last']}"
)

if keyword.lower().strip() != data["keyword"].lower():
    st.info(
        "This deployment currently displays the most recently generated "
        f"analysis for **{data['keyword']}**. The local pipeline can generate "
        "a new analysis for another healthcare keyword."
    )

st.divider()

# ---------------------------------------------------------
# TOP NARRATIVES SUMMARY
# ---------------------------------------------------------

st.subheader("Top observed health narratives")

st.caption(
    "Narratives are ranked by observed recurrence and participation, with "
    "engagement used as a secondary signal. A repeated meme requires "
    "independent recurrence; a one-off valid claim is labeled emerging."
)

summary_cols = st.columns(3)

for i, narrative in enumerate(data["narratives"]):

    with summary_cols[i]:

        priority = narrative["priority"]

        diffusion = narrative["diffusion"]

        st.markdown(
            f"### {priority['flag']} Narrative {narrative['rank']}"
        )

        st.write(narrative["claim"])

        maturity = narrative["maturity"].replace("_", " ")

        st.caption(f"**{maturity}**")

        st.metric(
            "Observed posts",
            diffusion["observed_posts"]
        )

        st.metric(
            "Unique participants",
            diffusion["unique_participants"]
        )

        if fast_mode:
            st.metric(
                "Evidence analysis",
                "NOT RUN"
            )
        else:
            st.metric(
                "Evidence divergence",
                narrative["divergence"]["level"]
            )

        if fast_mode:
            st.markdown(
                f"**Cultural signal:** "
                f"{priority['label'].replace('_', ' ')}"
            )
        else:
            st.markdown(
                f"**Priority:** "
                f"{priority['label'].replace('_', ' ')}"
            )

st.divider()

# ---------------------------------------------------------
# DETAILED ANALYSIS FOR EACH NARRATIVE
# ---------------------------------------------------------

for narrative in data["narratives"]:

    rank = narrative["rank"]
    claim = narrative["claim"]
    diffusion = narrative["diffusion"]
    dna = narrative["meme_dna"]
    evidence = narrative["evidence"]
    divergence = narrative["divergence"]
    behavior = narrative["behavior"]
    priority = narrative["priority"]

    deep_cache = (
        find_deep_cache(claim)
        if fast_mode
        else None
    )

    st.header(f"Narrative {rank}")

    st.markdown(f"### {claim}")

    maturity_label = narrative["maturity"].replace("_", " ")

    if narrative["maturity"] == "REPEATED_MEME":
        st.success(f"Maturity: {maturity_label}")
    else:
        st.info(f"Maturity: {maturity_label}")

    # -----------------------------------------------------
    # DIFFUSION
    # -----------------------------------------------------

    st.markdown("#### 1. Cultural diffusion")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Observed posts",
        diffusion["observed_posts"]
    )

    c2.metric(
        "Unique participants",
        diffusion["unique_participants"]
    )

    velocity = diffusion["posts_per_hour"]

    c3.metric(
        "Posts / hour",
        f"{velocity:.2f}" if velocity is not None else "N/A"
    )

    c4.metric(
        "Max observed reposts",
        diffusion["max_retweets"]
    )

    d1, d2, d3 = st.columns(3)

    d1.metric(
        "Persistence",
        f"{diffusion['persistence_minutes']:.0f} min"
    )

    d2.metric(
        "Max likes",
        diffusion["max_likes"]
    )

    d3.metric(
        "Max views",
        diffusion["max_views"]
    )

    st.caption(
        "Metrics describe the analyzed Calcifer observation window, "
        "not global social-media activity."
    )

    # -----------------------------------------------------
    # MEME DNA
    # -----------------------------------------------------

    st.markdown("#### 2. Meme DNA")

    mutation_status = dna["mutation_status"]

    st.write(
        "**Mutation status:**",
        mutation_status.replace("_", " ")
    )

    st.write(
        "**Distinct observed variants:**",
        dna["distinct_variants"]
    )

    if mutation_status == "REPLICATION_WITHOUT_OBSERVED_MUTATION":
        st.info(
            "The narrative appeared across multiple posts, but the "
            "high-confidence wording remained effectively unchanged. "
            "This is faithful replication rather than observed mutation."
        )

    elif mutation_status == "INSUFFICIENT_FOR_MUTATION_ANALYSIS":
        st.info(
            "Only one high-confidence occurrence was observed, so semantic "
            "mutation cannot yet be measured."
        )

    else:
        for mutation in dna["mutations"]:
            st.write(
                f"{mutation['from']} → {mutation['to']}: "
                f"semantic mutation {mutation['semantic_mutation']}"
            )

    with st.expander("View observed variants"):
        for variant in dna["variants"]:
            st.markdown(
                f"**{variant['variant']} · "
                f"{variant['observed_count']} post(s) · "
                f"{variant['unique_authors']} author(s)**"
            )
            st.write(variant["text"])

    # -----------------------------------------------------
    # SCIENTIFIC EVIDENCE
    # -----------------------------------------------------

    st.markdown("#### 3. Scientific evidence")

    if fast_mode:
        st.info(
            "Scientific evidence analysis was not run during Fast Scan. "
            "Deep Analysis retrieves and evaluates scientific literature "
            "for this narrative."
        )
    else:
        st.markdown(
            f"### Verdict: {evidence['verdict']}"
        )

        st.write(evidence["summary"])

        with st.expander("View retrieved scientific sources"):

            for source in evidence["sources"]:

                pmid = source.get("pmid")
                year = source.get("year", "")
                title = source.get("title", "")
                relevance = source.get(
                    "semantic_relevance",
                    ""
                )

                if pmid:
                    st.markdown(
                        f"**[{year} · PMID {pmid}]"
                        f"(https://pubmed.ncbi.nlm.nih.gov/{pmid}/)**"
                    )
                else:
                    st.markdown(f"**[{year}] {title}**")

                st.write(title)

                if relevance != "":
                    st.caption(
                        f"Retrieval similarity: {relevance} "
                        "(relevance signal only, not evidence strength)"
                    )

                st.markdown("---")

    # -----------------------------------------------------
    # MEME–EVIDENCE DIVERGENCE
    # -----------------------------------------------------

    st.markdown("#### 4. Meme–Evidence Divergence")

    if fast_mode:
        st.info(
            "Not calculated in Fast Scan. Divergence requires scientific "
            "evidence analysis before comparing the cultural narrative "
            "against the evidence baseline."
        )
    else:
        e1, e2 = st.columns(2)

        e1.metric(
            "Evidence alignment",
            divergence["alignment"]
        )

        e2.metric(
            "Divergence",
            divergence["level"]
        )

        st.caption(
            "Divergence compares what the narrative claims with what the "
            "retrieved evidence supports. It is not a popularity score."
        )

    # -----------------------------------------------------
    # BEHAVIOR
    # -----------------------------------------------------

    st.markdown("#### 5. Belief → behavior")

    if fast_mode:
        st.info(
            "Behavioral activation was not analyzed in Fast Scan. "
            "Deep Analysis checks for explicit recommendations, avoidance, "
            "treatment changes, and behavioral intention."
        )
    else:
        b1, b2 = st.columns(2)

        b1.metric(
            "Behavior-signal posts",
            f"{behavior['posts']} / {diffusion['observed_posts']}"
        )

        b2.metric(
            "Behavior signal rate",
            f"{behavior['rate'] * 100:.1f}%"
        )

        if behavior["detected"]:
            st.warning(
                "At least one post contains an explicit recommendation, "
                "intention, avoidance, or other behavioral signal."
            )
        else:
            st.caption(
                "No explicit behavioral-intention signal was detected. "
                "Repetition alone is not treated as proof of behavior."
            )

    # -----------------------------------------------------
    # PRIORITY
    # -----------------------------------------------------

    if fast_mode:
        st.markdown("#### 6. Cultural recurrence signal")

        st.markdown(
            f"### {priority['flag']} "
            f"{priority['label'].replace('_', ' ')}"
        )

        st.write(priority["rationale"])

        st.caption(
            "This is a cultural transmission signal only. "
            "No public-health risk classification is assigned until "
            "evidence and behavioral analysis are completed."
        )
    else:
        st.markdown("#### 6. Public-health priority")

        st.markdown(
            f"### {priority['flag']} "
            f"{priority['label'].replace('_', ' ')}"
        )

        st.write(priority["rationale"])

    if fast_mode:
        p1, p2 = st.columns(2)

        p1.metric(
            "Observed recurrence",
            "REPEATED"
            if narrative["maturity"] == "REPEATED_MEME"
            else "EMERGING"
        )

        p2.metric(
            "Scientific assessment",
            "NOT RUN"
        )

    else:
        p1, p2, p3 = st.columns(3)

        p1.metric(
            "Spread",
            "REPEATED"
            if narrative["maturity"] == "REPEATED_MEME"
            else "EMERGING"
        )

        p2.metric(
            "Evidence divergence",
            divergence["level"]
        )

        p3.metric(
            "Behavior",
            "YES" if behavior["detected"] else "NO"
        )

    # -----------------------------------------------------
    # DEEP ANALYSIS
    # -----------------------------------------------------

    if fast_mode:

        st.markdown("#### 7. Deep Analysis")

        if deep_cache:

            st.success(
                "⚡ Cached · instant"
            )

            if st.button(
                "Deep Analysis",
                key=f"open_deep_{rank}",
                type="primary"
            ):
                st.session_state["deep_analysis_rank"] = rank

            if st.session_state.get("deep_analysis_rank") == rank:

                st.markdown("---")
                st.markdown(
                    f"## 🧬 Deep Analysis: {deep_cache['title']}"
                )

                # -------------------------------------------------
                # CULTURAL DIFFUSION VISUALIZATION
                # -------------------------------------------------

                st.markdown("### Cultural diffusion")

                deep_diffusion = deep_cache.get("diffusion", {})

                observed_posts = deep_diffusion.get(
                    "observed_posts", 0
                ) or 0

                unique_participants = deep_diffusion.get(
                    "unique_participants", 0
                ) or 0

                # -----------------------------------------
                # STORY 1: CULTURAL FOOTPRINT
                # -----------------------------------------

                behavior_snapshot = deep_cache.get(
                    "behavior",
                    {}
                )

                behavior_signal_posts = (
                    behavior_snapshot.get(
                        "signal_posts",
                        0
                    )
                    or 0
                )

                footprint_df = pd.DataFrame({
                    "Signal": [
                        "Observed posts",
                        "Unique participants",
                        "Behavior-signal posts"
                    ],
                    "Count": [
                        observed_posts,
                        unique_participants,
                        behavior_signal_posts
                    ]
                })

                st.markdown(
                    "#### What is spreading?"
                )

                footprint_chart = (
                    alt.Chart(footprint_df)
                    .mark_bar(
                        cornerRadiusEnd=5
                    )
                    .encode(
                        y=alt.Y(
                            "Signal:N",
                            sort=None,
                            title=None
                        ),
                        x=alt.X(
                            "Count:Q",
                            title="Observed count"
                        ),
                        tooltip=[
                            alt.Tooltip(
                                "Signal:N",
                                title="Signal"
                            ),
                            alt.Tooltip(
                                "Count:Q",
                                title="Count",
                                format=","
                            )
                        ]
                    )
                    .properties(
                        height=150
                    )
                )

                st.altair_chart(
                    footprint_chart,
                    use_container_width=True
                )

                st.caption(
                    "Cultural footprint separates how often "
                    "the narrative appeared, how many distinct "
                    "participants carried it, and whether posts "
                    "contained explicit behavioral language."
                )

                d1, d2, d3 = st.columns(3)

                d1.metric(
                    "Observed posts",
                    observed_posts
                )

                d2.metric(
                    "Unique participants",
                    unique_participants
                )

                posts_per_hour = deep_diffusion.get(
                    "posts_per_hour"
                )

                d3.metric(
                    "Posts / hour",
                    (
                        f"{posts_per_hour:.2f}"
                        if isinstance(posts_per_hour, (int, float))
                        else "—"
                    )
                )

                # Evidence
                deep_evidence = deep_cache["evidence"]

                st.markdown("### Scientific evidence")

                st.metric(
                    "Evidence verdict",
                    deep_evidence["verdict"].replace("_", " ")
                )

                st.write(
                    deep_evidence.get("summary", "")
                )

                with st.expander(
                    "View scientific evidence sources"
                ):

                    for source in deep_evidence.get(
                        "sources", []
                    ):

                        pmid = source.get("pmid")
                        year = source.get("year", "")
                        study_type = source.get(
                            "study_type",
                            "Study"
                        )

                        if pmid:
                            st.markdown(
                                f"**[{study_type} · {year} · "
                                f"PMID {pmid}]"
                                f"(https://pubmed.ncbi.nlm.nih.gov/{pmid}/)**"
                            )
                        else:
                            st.markdown(
                                f"**{study_type} · {year}**"
                            )

                        if source.get("finding"):
                            st.write(
                                "**Finding:**",
                                source["finding"]
                            )

                        if source.get("limitation"):
                            st.write(
                                "**Limitation:**",
                                source["limitation"]
                            )

                        st.markdown("---")

                # Meme DNA
                st.markdown("### Meme DNA")

                variants = deep_cache["meme_dna"]["variants"]

                # Visual Meme DNA graph
                if variants:

                    # -----------------------------------------
                    # STORY 2: NARRATIVE MUTATION
                    # -----------------------------------------

                    mutations = deep_cache.get(
                        "meme_dna",
                        {}
                    ).get(
                        "semantic_mutations",
                        []
                    )

                    mutation_rows = []

                    for mutation in mutations:

                        source = str(
                            mutation.get(
                                "from",
                                "?"
                            )
                        )

                        target = str(
                            mutation.get(
                                "to",
                                "?"
                            )
                        )

                        distance = mutation.get(
                            "distance"
                        )

                        similarity = mutation.get(
                            "cosine_similarity"
                        )

                        if isinstance(
                            distance,
                            (int, float)
                        ):

                            mutation_rows.append({
                                "Transition": (
                                    f"{source} → {target}"
                                ),
                                "Semantic distance": (
                                    float(distance)
                                ),
                                "Cosine similarity": (
                                    float(similarity)
                                    if isinstance(
                                        similarity,
                                        (int, float)
                                    )
                                    else None
                                )
                            })

                    if mutation_rows:

                        st.markdown(
                            "#### How much did the "
                            "narrative change?"
                        )

                        mutation_df = pd.DataFrame(
                            mutation_rows
                        )

                        mutation_chart = (
                            alt.Chart(
                                mutation_df
                            )
                            .mark_bar(
                                cornerRadiusEnd=5
                            )
                            .encode(
                                y=alt.Y(
                                    "Transition:N",
                                    sort=None,
                                    title=None
                                ),
                                x=alt.X(
                                    "Semantic distance:Q",
                                    title=(
                                        "Semantic distance"
                                    ),
                                    scale=alt.Scale(
                                        domain=[0, 1]
                                    )
                                ),
                                tooltip=[
                                    alt.Tooltip(
                                        "Transition:N"
                                    ),
                                    alt.Tooltip(
                                        "Semantic distance:Q",
                                        format=".3f"
                                    ),
                                    alt.Tooltip(
                                        "Cosine similarity:Q",
                                        format=".3f"
                                    )
                                ]
                            )
                            .properties(
                                height=max(
                                    110,
                                    len(
                                        mutation_rows
                                    ) * 48
                                )
                            )
                        )

                        st.altair_chart(
                            mutation_chart,
                            use_container_width=True
                        )

                        st.caption(
                            "Higher semantic distance means "
                            "the wording or meaning changed "
                            "more between observed variants."
                        )

                # Keep the underlying variant text visible below the graph.
                for variant in variants:
                    st.markdown(
                        f"**{variant.get('id', '?')} — "
                        f"{variant.get('claim', '')}**"
                    )

                    st.caption(
                        "Evidence alignment: "
                        + str(
                            variant.get(
                                "evidence_alignment",
                                "UNKNOWN"
                            )
                        ).replace("_", " ")
                    )

                # Divergence
                st.markdown(
                    "### Meme–Evidence Divergence"
                )

                deep_divergence = deep_cache["divergence"]

                d1, d2 = st.columns(2)

                d1.metric(
                    "Overall divergence",
                    deep_divergence["overall_level"]
                )

                d2.metric(
                    "Largest divergence",
                    deep_divergence[
                        "largest_divergence"
                    ]
                )

                st.write(
                    deep_divergence.get(
                        "baseline",
                        ""
                    )
                )

                st.write(
                    deep_divergence.get(
                        "interpretation",
                        ""
                    )
                )

                # -------------------------------------------------
                # -------------------------------------------------
                # STORY 3: SCIENTIFIC EVIDENCE LANDSCAPE
                # -------------------------------------------------

                st.markdown(
                    "### Scientific evidence landscape"
                )

                evidence_sources = (
                    deep_evidence.get(
                        "sources",
                        []
                    )
                )

                relationship_order = [
                    "SUPPORTS",
                    "PARTIAL",
                    "CONTRADICTS",
                    "RELATED_ONLY"
                ]

                relationship_labels = {
                    "SUPPORTS": "Supports",
                    "PARTIAL": "Partial",
                    "CONTRADICTS": "Contradicts",
                    "RELATED_ONLY": "Related only"
                }

                relationship_counts = {
                    key: 0
                    for key in relationship_order
                }

                for source in evidence_sources:

                    relationship = str(
                        source.get(
                            "relationship",
                            "RELATED_ONLY"
                        )
                    ).upper()

                    if relationship not in (
                        relationship_counts
                    ):
                        relationship = (
                            "RELATED_ONLY"
                        )

                    relationship_counts[
                        relationship
                    ] += 1

                evidence_landscape_df = (
                    pd.DataFrame([
                        {
                            "Relationship": (
                                relationship_labels[
                                    key
                                ]
                            ),
                            "Papers": (
                                relationship_counts[
                                    key
                                ]
                            )
                        }
                        for key
                        in relationship_order
                    ])
                )

                evidence_chart = (
                    alt.Chart(
                        evidence_landscape_df
                    )
                    .mark_bar(
                        cornerRadiusEnd=5
                    )
                    .encode(
                        y=alt.Y(
                            "Relationship:N",
                            sort=[
                                "Supports",
                                "Partial",
                                "Contradicts",
                                "Related only"
                            ],
                            title=None
                        ),
                        x=alt.X(
                            "Papers:Q",
                            title=(
                                "Retrieved papers"
                            ),
                            axis=alt.Axis(
                                tickMinStep=1
                            )
                        ),
                        tooltip=[
                            alt.Tooltip(
                                "Relationship:N",
                                title="Evidence"
                            ),
                            alt.Tooltip(
                                "Papers:Q",
                                title="Papers",
                                format=".0f"
                            )
                        ]
                    )
                    .properties(
                        height=180
                    )
                )

                st.altair_chart(
                    evidence_chart,
                    use_container_width=True
                )

                st.caption(
                    "Retrieved studies are grouped by how "
                    "directly they support, contradict, "
                    "partially address, or are merely related "
                    "to the central health proposition."
                )

                # Behavior

                st.markdown("### Belief → behavior")

                deep_behavior = deep_cache["behavior"]

                b1, b2 = st.columns(2)

                b1.metric(
                    "Behavior-signal posts",
                    f"{deep_behavior['signal_posts']} / "
                    f"{deep_behavior['analyzed_posts']}"
                )

                b2.metric(
                    "Behavior signal rate",
                    f"{deep_behavior['rate'] * 100:.1f}%"
                )

                behavior_rate = float(
                    deep_behavior.get("rate", 0) or 0
                )

                behavior_rate = max(
                    0.0,
                    min(1.0, behavior_rate)
                )

                st.progress(behavior_rate)

                st.caption(
                    f"Behavioral activation: "
                    f"{behavior_rate * 100:.1f}%"
                )

                if not deep_behavior["detected"]:
                    st.caption(
                        "No explicit behavioral intention was "
                        "detected in the analyzed posts."
                    )

                # Priority
                st.markdown(
                    "### Public-health prioritization"
                )

                deep_priority = deep_cache["priority"]

                st.markdown(
                    f"## {deep_priority['flag']} "
                    f"{deep_priority['label']}"
                )

                st.write(
                    deep_priority["rationale"]
                )

        else:

            st.caption(
                "Fresh analysis · ~1–3 min"
            )

            if st.button(
                "Deep Analysis",
                key=f"fresh_deep_{rank}"
            ):

                with st.spinner(
                    f"Running Deep Analysis with "
                    f"{selected_model} as the primary model..."
                ):

                    result = subprocess.run(
                        [
                            sys.executable,
                            "run_deep_analysis.py",
                            str(rank),
                            selected_model
                        ],
                        capture_output=True,
                        text=True
                    )

                if result.returncode == 0:

                    st.success(
                        "Deep Analysis complete. "
                        "Loading evidence and visualizations..."
                    )

                    st.rerun()

                else:

                    st.error(
                        "Deep Analysis stopped before completion."
                    )

                    with st.expander(
                        "Show Deep Analysis error"
                    ):
                        st.code(
                            result.stdout
                            + "\n"
                            + result.stderr
                        )

    st.divider()

# ---------------------------------------------------------
# METHOD NOTE
# ---------------------------------------------------------

st.subheader("How Placebo Economy interprets the signal")

st.write(
    "A health narrative is not labeled harmful simply because it describes "
    "a negative outcome. Placebo Economy separates cultural diffusion, "
    "scientific evidence, meme–evidence divergence, semantic mutation, "
    "and behavioral activation before assigning a monitoring priority."
)

st.caption(
    "Current prototype results are based on a limited Calcifer observation "
    "window and automated evidence retrieval. They are analytical signals, "
    "not clinical conclusions."
)
