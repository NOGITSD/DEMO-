import os, yaml, json
import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime

from evc_engine import EVCEngine
from reflection import reflect
from core_llm import get_llm_core
from memory import Memory

# =====================================================
# Configuration
# =====================================================
st.set_page_config(
    page_title="EVC Hybrid Chat v3", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load config with error handling
try:
    cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
except Exception as e:
    st.error(f"❌ Cannot load config.yaml: {e}")
    st.stop()

# Initialize components
try:
    evc = EVCEngine(cfg)
    mem = Memory(cfg.get("memory", {}).get("path", "session_memory.json"))
    llm = get_llm_core()  # ✅ Initialize LLM Core
except Exception as e:
    st.error(f"❌ Initialization error: {e}")
    st.stop()

# =====================================================
# Sidebar Settings
# =====================================================
st.sidebar.title("⚙️ การตั้งค่า")

provider = os.getenv("LLM_PROVIDER", "offline").lower()
base_url = os.getenv("OPENAI_BASE_URL", "")
model = os.getenv("OPENAI_MODEL", os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini"))

st.sidebar.subheader("📌 สถานะการเชื่อมต่อ")
if provider == "offline":
    st.sidebar.error("📴 **Offline Mode**\nใช้ fallback replies")
else:
    st.sidebar.success(f"🟢 **Online Mode**\n**Provider:** {provider}\n**Model:** {model}")
    if base_url:
        st.sidebar.info(f"**Base URL:** {base_url}")

st.sidebar.divider()

# EVC Status
st.sidebar.subheader("📈 สถานะ EVC")
if "E_vals" in st.session_state and st.session_state.E_vals:
    current_E = st.session_state.E_vals[-1]
    current_K = st.session_state.K_vals[-1]
    current_phase = st.session_state.phase_vals[-1]
    
    st.sidebar.metric("Energy (E)", f"{current_E:.2f}", 
                     delta=f"{current_E - st.session_state.E_vals[-2]:.2f}" if len(st.session_state.E_vals) > 1 else None)
    st.sidebar.metric("Sensitivity (K)", f"{current_K:.2f}")
    st.sidebar.markdown(f"**Phase:** `{current_phase}`")
    
    # Show EVC info for debugging
    with st.sidebar.expander("🔍 EVC Debug Info"):
        st.json({
            "E": current_E,
            "K": current_K,
            "Phase": current_phase,
            "Last_dE": st.session_state.get("last_dE", 0.0)
        })
else:
    st.sidebar.info("เริ่มคุยเพื่อดูสถานะ EVC")

st.sidebar.divider()

# Controls
if st.sidebar.button("🗑️ ล้างประวัติ", use_container_width=True):
    st.session_state.chat_log = []
    st.session_state.E_vals = []
    st.session_state.K_vals = []
    st.session_state.phase_vals = []
    st.session_state.last_dE = 0.0
    st.rerun()

if st.sidebar.button("💾 บันทึก Session", use_container_width=True):
    try:
        mem.flush()
        st.sidebar.success("✅ บันทึกเรียบร้อย")
    except Exception as e:
        st.sidebar.error(f"❌ บันทึกล้มเหลว: {e}")

# =====================================================
# Initialize Session State
# =====================================================
if "chat_log" not in st.session_state: 
    st.session_state.chat_log = []
if "E_vals" not in st.session_state:   
    st.session_state.E_vals = []
if "K_vals" not in st.session_state:   
    st.session_state.K_vals = []
if "phase_vals" not in st.session_state: 
    st.session_state.phase_vals = []
if "last_dE" not in st.session_state:
    st.session_state.last_dE = 0.0
if "processing" not in st.session_state:
    st.session_state.processing = False

# =====================================================
# Main UI
# =====================================================
st.title("🤖 EVC Hybrid Chat – v3")
st.caption("💬 Serious conversation + 🧠 EVC self-evaluation • 🌐 Web UI + 📊 Debug Dashboard")

col1, col2 = st.columns([2.2, 1.0])

# =====================================================
# Chat Interface (Left Column)
# =====================================================
with col1:
    st.subheader("💬 บทสนทนา")
    
    # Input form
    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "คุณ:", 
            placeholder="พิมพ์ข้อความของคุณที่นี่...",
            height=100,
            key="user_input"
        )
        submit = st.form_submit_button("📤 ส่งข้อความ", use_container_width=True)
    
    # Process input
    if submit and user_input.strip() and not st.session_state.processing:
        st.session_state.processing = True
        
        with st.spinner("🤔 กำลังประมวลผล..."):
            try:
                # Step 1: Update EVC from user input
                info1 = evc.update_from_text(user_input)
                st.session_state.last_dE = info1.get("dE", 0.0)
                
                # Step 2: Get tone based on current phase
                tone = evc.tone_from_phase(cfg.get("tone_map", {}))
                system_prompt = f"You are a helpful assistant.\nTone: {tone}\nRespond in Thai language."
                
                # Step 3: Generate response WITH EVC state ✅
                current_evc_state = {
                    "E": evc.E,
                    "K": evc.K,
                    "phase": evc._phase(),
                    "dE": info1.get("dE", 0.0)
                }
                
                raw_answer = llm.generate(
                    prompt=user_input,
                    system_prompt=system_prompt,
                    mode="chat",
                    evc_state=current_evc_state  # ✅ Send EVC context
                )
                
                # Check for errors
                if raw_answer.startswith("⚠️"):
                    st.error(raw_answer)
                    answer = "ขออภัยค่ะ ระบบมีปัญหาชั่วคราว กรุณาลองใหม่อีกครั้ง"
                else:
                    answer = raw_answer
                
                # Step 4: Reflect on conversation
                try:
                    rvec = reflect(user_input, answer)
                except Exception as e:
                    st.warning(f"⚠️ Reflection failed: {e}")
                    rvec = {
                        "coherence": 0.5,
                        "toxicity": 0.0,
                        "satisfaction": 0.5,
                        "verbosity": 0.5
                    }
                
                # Step 5: Update EVC from reflection
                info2 = evc.update_from_reflection(rvec)
                
                # Step 6: Save to session
                st.session_state.chat_log.append((user_input, answer))
                st.session_state.E_vals.append(info2["E"])
                st.session_state.K_vals.append(info2.get("K", 0.0))
                st.session_state.phase_vals.append(info2["phase"])
                
                # Step 7: Save to memory
                try:
                    mem.save_turn(user_input, answer, info2, rvec)
                except Exception as e:
                    st.warning(f"⚠️ Memory save failed: {e}")
                
                st.session_state.processing = False
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error: {e}")
                import traceback
                st.exception(e)
                st.session_state.processing = False
    
    # Display chat history
    st.divider()
    
    if st.session_state.chat_log:
        for i, (u, a) in enumerate(reversed(st.session_state.chat_log), 1):
            turn = len(st.session_state.chat_log) - i + 1
            
            with st.container():
                st.markdown(f"**Turn {turn}**")
                st.markdown(f"🧍 **คุณ:** {u}")
                st.markdown(f"🤖 **ผู้ช่วย:** {a}")
                
                # Show EVC values for this turn
                if turn <= len(st.session_state.E_vals):
                    idx = turn - 1
                    cols = st.columns(4)
                    cols[0].metric("E", f"{st.session_state.E_vals[idx]:.2f}")
                    cols[1].metric("K", f"{st.session_state.K_vals[idx]:.2f}")
                    cols[2].metric("Phase", st.session_state.phase_vals[idx])
                    if idx < len(st.session_state.E_vals) - 1:
                        dE = st.session_state.E_vals[idx] - st.session_state.E_vals[idx-1] if idx > 0 else 0
                        cols[3].metric("ΔE", f"{dE:.2f}", delta=f"{dE:+.2f}")
                
                st.divider()
    else:
        st.info("👋 เริ่มต้นบทสนทนา พิมพ์ข้อความด้านบน")

# =====================================================
# Dashboard (Right Column)
# =====================================================
with col2:
    st.subheader("📊 EVC Dashboard")
    
    if st.session_state.E_vals:
        # Energy (E) Chart
        with st.container():
            fig1, ax1 = plt.subplots(figsize=(6, 3))
            turns = list(range(1, len(st.session_state.E_vals) + 1))
            ax1.plot(turns, st.session_state.E_vals, marker="o", color="#FF6B6B", linewidth=2, label="E")
            ax1.axhline(y=0.25, color="gray", linestyle="--", alpha=0.5, label="Fear threshold")
            ax1.axhline(y=1.1, color="red", linestyle="--", alpha=0.5, label="Overheat threshold")
            ax1.set_title("Energy (E) Trend", fontsize=12, fontweight="bold")
            ax1.set_xlabel("Turn")
            ax1.set_ylabel("E Value")
            ax1.grid(True, alpha=0.3)
            ax1.set_ylim([0, 1.5])
            ax1.legend(fontsize=8)
            st.pyplot(fig1)
            plt.close()
        
        # Sensitivity (K) Chart
        with st.container():
            fig2, ax2 = plt.subplots(figsize=(6, 3))
            ax2.plot(turns, st.session_state.K_vals, marker="s", color="#4ECDC4", linewidth=2, label="K")
            ax2.set_title("Sensitivity (K) Trend", fontsize=12, fontweight="bold")
            ax2.set_xlabel("Turn")
            ax2.set_ylabel("K Value")
            ax2.grid(True, alpha=0.3)
            ax2.set_ylim([0.2, 0.8])
            ax2.legend(fontsize=8)
            st.pyplot(fig2)
            plt.close()
        
        # Phase Distribution
        st.subheader("📄 Phase Distribution")
        from collections import Counter
        phase_counts = Counter(st.session_state.phase_vals)
        for phase, count in sorted(phase_counts.items()):
            percentage = (count / len(st.session_state.phase_vals)) * 100
            st.progress(percentage / 100, text=f"{phase}: {count} ({percentage:.1f}%)")
        
        # Latest Phase with Emoji
        latest_phase = st.session_state.phase_vals[-1]
        phase_emoji = {
            "calm": "😌",
            "focus": "🎯",
            "overheat": "🔥",
            "fear": "😨",
            "cooldown": "❄️"
        }
        st.markdown(f"### {phase_emoji.get(latest_phase, '📊')} Current Phase")
        st.markdown(f"**`{latest_phase.upper()}`**")
        
        # Statistics
        st.divider()
        st.subheader("📈 Statistics")
        col_a, col_b = st.columns(2)
        col_a.metric("Avg E", f"{sum(st.session_state.E_vals)/len(st.session_state.E_vals):.2f}")
        col_b.metric("Avg K", f"{sum(st.session_state.K_vals)/len(st.session_state.K_vals):.2f}")
        
        col_c, col_d = st.columns(2)
        col_c.metric("Max E", f"{max(st.session_state.E_vals):.2f}")
        col_d.metric("Min E", f"{min(st.session_state.E_vals):.2f}")
        
        # EVC Info Box
        st.divider()
        with st.expander("ℹ️ EVC Framework Info"):
            st.markdown("""
            **EVC (Energy Value Conservation)** คือระบบวิเคราะห์พลังงานของ AI
            
            - **E (Energy)**: ระดับพลังงาน/ความมั่นใจ (0-1.5)
            - **K (Stability)**: ความเสถียรของระบบ (0.25-0.75)
            - **Phase**: สถานะปัจจุบัน (calm, focus, fear, overheat, cooldown)
            
            🎯 ระบบปรับ tone การตอบของ AI ตามสถานะปัจจุบัน
            """)
        
    else:
        st.info("📊 เริ่มต้นบทสนทนาเพื่อดู Dashboard")

# =====================================================
# Footer
# =====================================================
st.divider()
st.caption(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 💾 Total Turns: {len(st.session_state.chat_log)} | 🔧 EVC v3.1 (LLM Context-Aware)")