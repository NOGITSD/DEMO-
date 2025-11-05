
from typing import List
POS_WORDS = {
    "ดีมาก","เยี่ยม","สุดยอด","ขอบคุณ","สวย","เก่ง","ถูกต้อง","ชัดเจน","แม่นยำ",
    "รัก","แนะนำ","ยินดี","ยอดเยี่ยม","เวิร์ก","เวิร์ค","เหมาะสม","ก้าวหน้า","สำเร็จ"
}
NEG_WORDS = {
    "แย่","ไม่ดี","ผิด","พัง","โกรธ","กลัว","กังวล","ห่วย","งง","สับสน","ล้มเหลว",
    "ยาก","แย่มาก","ช้า","น่ากลัว","แย่สุดๆ"
}
VOL_WORDS = {"เร่งด่วน","ด่วน","วิกฤต","ผันผวน","แรง","แรงมาก","สวิง","ผันผวนสูง"}

def simple_sentiment(text: str) -> float:
    t = text.lower()
    pos = sum(1 for w in POS_WORDS if w in t)
    neg = sum(1 for w in NEG_WORDS if w in t)
    if pos == 0 and neg == 0:
        return 0.0
    score = (pos - neg) / max(1, pos + neg)
    return max(-1.0, min(1.0, score))

def volatility_hint(text: str) -> float:
    t = text.lower()
    vol = sum(1 for w in VOL_WORDS if w in t)
    return min(1.0, vol / 3.0)

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))
