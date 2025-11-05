# ============================================================
# EVC Hybrid Chat v3 - Configuration for Ollama (gpt-oss:120b)
# ============================================================

# ⚙️ LLM Provider Settings
LLM_PROVIDER=ollama
OPENAI_BASE_URL=http://localhost:11434
OPENAI_MODEL=gpt-oss:120b-cloud

# 🔑 API Key (not needed for local Ollama, but set for compatibility)
OPENAI_API_KEY=local-ollama

# 📡 Debug & Logging
DEBUG_LOG=true

# 💾 Memory & Storage
MEMORY_PATH=session_memory.json
SELFPLAY_OUTPUT_DIR=data/

# 🎯 Self-Play Settings
SELFPLAY_EPISODES=3
SELFPLAY_MAX_TURNS=6
SELFPLAY_MODE_PATTERN=chat,evc,chat,evc,chat,evc

# 🌐 Streamlit Settings (optional)
STREAMLIT_SERVER_PORT=8501
STREAMLIT_LOGGER_LEVEL=warning

# ============================================================
# Windows: Use 'setx' to set environment variables
# ============================================================
# setx LLM_PROVIDER ollama
# setx OPENAI_BASE_URL http://localhost:11434
# setx OPENAI_MODEL gpt-oss:120b-cloud
# setx DEBUG_LOG true

# ============================================================
# Linux/Mac: Use 'export' in .bashrc or .zshrc
# ============================================================
# export LLM_PROVIDER=ollama
# export OPENAI_BASE_URL=http://localhost:11434
# export OPENAI_MODEL=gpt-oss:120b-cloud
# export DEBUG_LOG=true

# ============================================================
# Or use with 'python -m' command
# ============================================================
# export LLM_PROVIDER=ollama && export OPENAI_BASE_URL=http://localhost:11434 && streamlit run web.py
