
from typing import Dict, Any
from utils import simple_sentiment, volatility_hint, clamp

class EVCEngine:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        evc = cfg.get("evc", {})
        self.E = evc.get("E_init", 0.5)
        self.loss = evc.get("loss", 0.02)
        self.K = evc.get("K", 0.45)
        self.clamp_low = evc.get("clamp_low", 0.0)
        self.clamp_high = evc.get("clamp_high", 1.5)
        self.overheat_th = evc.get("overheat_threshold", 1.1)
        self.fear_th = evc.get("fear_threshold", 0.25)
        self.cooldown_m = evc.get("cooldown_margin", 0.05)
        self._stability = 0.5

    def _phase(self) -> str:
        if self.E >= self.overheat_th:
            return "overheat"
        if self.E <= self.fear_th:
            return "fear"
        if abs(self.E - 0.5) <= self.cooldown_m:
            return "cooldown"
        if self.E > 0.55:
            return "focus"
        return "calm"

    def update_from_text(self, user_text: str) -> Dict[str, Any]:
        sent = simple_sentiment(user_text)
        vol  = volatility_hint(user_text)
        dE = self.K * (0.25*sent + 0.35*vol)
        self.E = clamp(self.E + dE - self.loss, self.clamp_low, self.clamp_high)
        return {"E": self.E, "phase": self._phase(), "dE": dE, "source": "perception"}

    def update_from_reflection(self, vector: Dict[str, float]) -> Dict[str, Any]:
        coh = vector.get("coherence", 0.6)
        tox = vector.get("toxicity", 0.0)
        sat = vector.get("satisfaction", 0.5)
        verb= vector.get("verbosity", 0.5)
        dE = self.K * ( -0.3*coh + 0.4*tox - 0.2*sat + 0.05*verb )
        self.E = clamp(self.E + dE - 0.5*self.loss, self.clamp_low, self.clamp_high)
        target_stability = 1.0 - min(1.0, abs(self.E-0.5))
        self._stability = 0.8*self._stability + 0.2*target_stability
        self.K = clamp(self.K * (0.98 + 0.04*self._stability), 0.25, 0.75)
        return {"E": self.E, "phase": self._phase(), "dE": dE, "source": "reflection", "K": self.K}

    def tone_from_phase(self, tone_map: Dict[str, str]) -> str:
        return tone_map.get(self._phase(), "เป็นทางการ สุภาพ ชัดเจน")
