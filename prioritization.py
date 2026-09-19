def prioritize(
    evidence_aligned,
    observed_momentum,
    behavioral_intent_detected
):
    if evidence_aligned and observed_momentum:
        return {
            "category": "HEALTHY_DIFFUSION",
            "label": "Healthy diffusion",
            "reason": "Evidence-aligned narrative with observed cultural momentum."
        }

    if evidence_aligned and not observed_momentum:
        return {
            "category": "CULTURALLY_OVERLOOKED",
            "label": "Culturally overlooked",
            "reason": "Evidence-backed narrative with limited observed cultural traction."
        }

    if (
        not evidence_aligned
        and observed_momentum
        and behavioral_intent_detected
    ):
        return {
            "category": "PRIORITY_SIGNAL",
            "label": "Priority signal",
            "reason": "Evidence-divergent narrative is spreading and explicit behavioral intention is present."
        }

    if not evidence_aligned:
        return {
            "category": "WATCH",
            "label": "Watch",
            "reason": "Evidence divergence is present, but explicit behavioral activation was not detected."
        }

    return {
        "category": "MONITOR",
        "label": "Monitor",
        "reason": "No strong prioritization signal detected."
    }


result = prioritize(
    evidence_aligned=False,
    observed_momentum=True,
    behavioral_intent_detected=False
)

print("\nPUBLIC-HEALTH PRIORITIZATION\n")
print("Category:", result["label"])
print("Reason:", result["reason"])
