
# EVC Hybrid Chat — v3 (Web UI + EVC Debug + Self-Play)

**New in v3**
- Web UI with **EVC Debug Dashboard** (energy E, phase, K dynamics)
- **AI‑vs‑AI Self‑Play trainer** to auto-generate conversation data for fine‑tuning (`data/selfplay.jsonl`)
- Connection indicator (Online vs Offline)

## Install
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

## Run Web UI
```bash
streamlit run web.py
```

## Run Self‑Play (AI talks to AI)
```bash
python selfplay_trainer.py --episodes 20 --max_turns 6 --topic "Debate: EVC vs LLM"
```

## Enable Real LLM (OpenAI‑compatible API)
```bash
# Provider name (any non-'offline' activates online path)
setx LLM_PROVIDER openai
setx OPENAI_API_KEY sk-...
setx OPENAI_BASE_URL https://api.openai.com/v1     # or http://localhost:11434/v1 for Ollama
setx OPENAI_MODEL gpt-4o-mini                      # or llama3 / mixtral, etc.
```
(restart terminal after `setx` on Windows)

---
Have fun! 🚀
