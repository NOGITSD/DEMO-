
import os, json, argparse, yaml
from evc_engine import EVCEngine
from reflection import reflect
from core_llm import generate

def run_episode(cfg, topic, max_turns=6):
    a = EVCEngine(cfg); b = EVCEngine(cfg)
    hist = []; who = 0; msg = f"เริ่มอภิปรายหัวข้อ: {topic}"
    for t in range(max_turns):
        eng = a if who==0 else b
        _ = eng.update_from_text(msg)
        tone = eng.tone_from_phase(cfg.get("tone_map", {}))
        reply = generate(msg, tone)
        rvec = reflect(msg, reply)
        info = eng.update_from_reflection(rvec)
        hist.append({"t": t, "speaker": "A" if who==0 else "B",
                     "prompt": msg, "reply": reply, "evc": info, "reflection": rvec})
        msg = reply; who = 1-who
    return {"topic": topic, "history": hist}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=10)
    ap.add_argument("--max_turns", type=int, default=6)
    ap.add_argument("--topic", type=str, default="อภิปรายข้อดีข้อเสียของ EVC เทียบกับ LLM")
    ap.add_argument("--out", type=str, default="data/selfplay.jsonl")
    args = ap.parse_args()

    cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for i in range(args.episodes):
            ep = run_episode(cfg, args.topic, args.max_turns)
            for h in ep["history"]:
                item = {"instruction": "ต่อบทสนทนาอย่างมีเหตุผลและจริงจัง โดยรักษาโทนตาม EVC phase",
                        "input": h["prompt"], "output": h["reply"],
                        "evc": h["evc"], "reflection": h["reflection"],
                        "topic": ep["topic"]}
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
            print(f"✓ episode {i+1}/{args.episodes} saved")
    print(f"saved to {args.out}")

if __name__ == "__main__":
    main()
