
from typing import Dict

def reflect(user_input: str, draft_answer: str) -> Dict[str, float]:
    coherence = min(1.0, (len(draft_answer)/300.0) + 0.2*(draft_answer.count("- ") + draft_answer.count("\n\n")))
    toxic_words = ["โง่","เกลียด","สวะ","ชัง","เถียง","หยาบคาย"]
    toxicity = 1.0 if any(w in draft_answer for w in toxic_words) else 0.0
    satisfaction = min(1.0, len(set(user_input.split()) & set(draft_answer.split())) / (len(set(user_input.split())) + 1e-6) + 0.2)
    verbosity = min(1.0, len(draft_answer)/800.0)
    def c01(x): return max(0.0, min(1.0, float(x)))
    return {"coherence": c01(coherence), "toxicity": c01(toxicity), "satisfaction": c01(satisfaction), "verbosity": c01(verbosity)}
