import streamlit as st

st.set_page_config(
    page_title="Placebo Economy",
    page_icon="🧬",
    layout="wide"
)

st.title("Placebo Economy")
st.subheader("Tracking how health narratives spread, mutate, diverge from evidence, and influence behavior.")

claim = st.text_input(
    "Enter a health claim",
    placeholder="e.g. Magnesium fixes insomnia"
)

if claim:
    st.write("Analyzing:", claim)
