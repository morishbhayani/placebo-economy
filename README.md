# Placebo Economy

**Placebo Economy tracks how health narratives spread, mutate, diverge from scientific evidence, and begin influencing behavior.**

Instead of asking only whether a claim is true or false, the system asks:

1. Is the narrative spreading?
2. What variants of the narrative are circulating?
3. How are those variants changing semantically?
4. How closely does each variant align with scientific evidence?
5. Is the narrative beginning to express behavioral intention?
6. Does it deserve public-health attention?

---

## Demo Narrative

Current prototype narrative:

> **“COVID-19 mRNA vaccines cause turbo cancer.”**

The prototype uses real social-media data from the Calcifer dataset and scientific literature retrieved through Europe PMC / PubMed.

---

## Pipeline

```text
Calcifer social posts
        ↓
Claim filtering + diffusion metrics
        ↓
Local Llama 3.2 semantic interpretation
        ↓
Claim / counter-claim detection
Normalized claims
Behavior classification
        ↓
Meme DNA + semantic distance
        ↓
Scientific evidence retrieval
        ↓
Meme–Evidence Divergence
        ↓
Public-health prioritization
