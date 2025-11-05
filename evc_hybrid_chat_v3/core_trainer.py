import os, json, time
from core_llm import generate

MEMORY_FILE = "EVC_memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sessions": []}

def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

def analyze_emotion(text):
    # วิเคราะห์ E,K,Phase จากข้อความของ AI
    if "E↑" in text: E = 1
    elif "E↓" in text: E = -1
    else: E = 0
    if "K↑" in text: K = 1
    elif "K↓" in text: K = -1
    else: K = 0
    if "Rising" in text: phase = "Rising"
    elif "Peak" in text: phase = "Peak"
    elif "Cooling" in text: phase = "Cooling"
    elif "Down" in text: phase = "Down"
    else: phase = "Neutral"
    return {"E": E, "K": K, "Phase": phase}

def train_loop(rounds=5):
    memory = load_memory()
    last_state = memory["sessions"][-1]["Phase"] if memory["sessions"] else "Neutral"

    for i in range(rounds):
        prompt = f"เฟสก่อนหน้า: {last_state}\nพูดคุยกันเพื่อปรับสมดุลของพลังงาน EVC"
        response = generate(prompt)
        state = analyze_emotion(response)

        memory["sessions"].append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "prompt": prompt,
            "response": response,
            **state
        })
        last_state = state["Phase"]
        print(f"[รอบ {i+1}] {state} | Response: {response[:80]}...")

    save_memory(memory)
    print("✅ บันทึกลง memory แล้ว:", MEMORY_FILE)

if __name__ == "__main__":
    train_loop(10)
