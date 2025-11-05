"""
🚀 Complete AI Chat System with Web Search & Context Memory
- Web search integration
- Context-aware conversation
- EVC emotion tracking
- Full working system
"""

import os
import json
import time
import yaml
import requests
import streamlit as st
from datetime import datetime
from typing import Dict, List, Any, Tuple
from collections import deque

# ============================================================
# 1. WEB SEARCH MODULE
# ============================================================

class WebSearcher:
    """ค้นหาข้อมูลจากเว็บโดยใช้ DuckDuckGo API"""
    
    def __init__(self):
        self.base_url = "https://duckduckgo.com/api"
        self.timeout = 10
    
    def search(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        """
        ค้นหาข้อมูลจากเว็บ
        Returns: [{"title": "...", "url": "...", "snippet": "..."}, ...]
        """
        try:
            # ใช้ DuckDuckGo search
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            }
            
            params = {
                'q': query,
                'format': 'json'
            }
            
            response = requests.get(
                self.base_url,
                params=params,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            results = []
            
            # Parse DuckDuckGo results
            for result in data.get('Results', [])[:max_results]:
                results.append({
                    'title': result.get('Title', 'N/A'),
                    'url': result.get('FirstURL', 'N/A'),
                    'snippet': result.get('Text', 'N/A')
                })
            
            # ถ้าหาไม่เจอจาก Results ให้ลองจาก RelatedTopics
            if not results:
                for topic in data.get('RelatedTopics', [])[:max_results]:
                    if 'Text' in topic:
                        results.append({
                            'title': topic.get('Text', 'N/A')[:50],
                            'url': topic.get('FirstURL', ''),
                            'snippet': topic.get('Text', 'N/A')
                        })
            
            return results
        
        except Exception as e:
            print(f"❌ Web search error: {str(e)}")
            return []
    
    def format_search_results(self, results: List[Dict]) -> str:
        """แปลงผลการค้นหาเป็น text format"""
        if not results:
            return "ไม่พบผลการค้นหา"
        
        formatted = "📊 ผลการค้นหา:\n\n"
        for i, result in enumerate(results, 1):
            formatted += f"{i}. **{result['title']}**\n"
            formatted += f"   🔗 {result['url']}\n"
            formatted += f"   📝 {result['snippet'][:150]}...\n\n"
        
        return formatted


# ============================================================
# 2. CONVERSATION MEMORY MODULE
# ============================================================

class ConversationMemory:
    """เก็บและจัดการประวัติการสนทนา"""
    
    def __init__(self, max_turns: int = 100):
        self.turns = deque(maxlen=max_turns)
        self.full_history = []
        self.search_cache = {}  # เก็บผลการค้นหา
    
    def add_turn(self, user_query: str, ai_response: str, 
                 search_used: bool = False, search_query: str = "",
                 evc_state: Dict = None):
        """เพิ่ม turn ใหม่"""
        turn = {
            "turn_number": len(self.full_history) + 1,
            "timestamp": datetime.now().isoformat(),
            "user_query": user_query,
            "ai_response": ai_response,
            "search_used": search_used,
            "search_query": search_query,
            "evc_state": evc_state or {}
        }
        
        self.turns.append(turn)
        self.full_history.append(turn)
    
    def get_context(self, recent_n: int = 10) -> str:
        """ดึงประวัติ N turn ล่าสุด"""
        recent = list(self.turns)[-recent_n:]
        
        context = "<conversation_history>\n"
        for turn in recent:
            context += f"  <turn number=\"{turn['turn_number']}\">\n"
            context += f"    <user>{turn['user_query'][:150]}</user>\n"
            context += f"    <assistant>{turn['ai_response'][:200]}</assistant>\n"
            if turn['search_used']:
                context += f"    <search_info>{turn['search_query']}</search_info>\n"
            context += f"  </turn>\n"
        context += "</conversation_history>\n"
        
        return context
    
    def cache_search(self, query: str, results: List[Dict]):
        """เก็บผลการค้นหาเพื่อไม่ต้องค้นหาซ้ำ"""
        self.search_cache[query.lower()] = {
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_cached_search(self, query: str) -> List[Dict] | None:
        """ดึงผลการค้นหาจากแคช (เก่าไม่เกิน 1 ชั่วโมง)"""
        cache_key = query.lower()
        if cache_key in self.search_cache:
            cached = self.search_cache[cache_key]
            cache_time = datetime.fromisoformat(cached['timestamp'])
            if (datetime.now() - cache_time).seconds < 3600:  # 1 hour
                return cached['results']
        return None


# ============================================================
# 3. FIXED CONTEXT BUILDER
# ============================================================

class ContextBuilder:
    """สร้าง system prompt ที่มี continuity"""
    
    @staticmethod
    def build_system_prompt(
        conversation_memory: ConversationMemory,
        current_turn: int,
        ai_name: str,
        user_query: str,
        evc_state: Dict,
        web_context: str = "",
        mode: str = "chat"
    ) -> str:
        """สร้าง system prompt ที่สมบูรณ์"""
        
        # ดึงประวัติ
        history = conversation_memory.get_context(recent_n=8)
        
        # Mandatory instructions
        mandatory = """
<MANDATORY>
✅ RULES:
1. อ้างอิงการสนทนาที่ผ่านมา ("จากที่คุณถาม...", "ต่อจากเมื่อกี้...")
2. ถ้าค้นหาข้อมูล ให้บอกว่า "จากการค้นหา..."
3. ไม่ให้ถามซ้ำ ให้เข้าใจบริบท
4. ตอบในภาษาไทย
</MANDATORY>
"""
        
        # EVC tone
        phase_tone = {
            "calm": "สุภาพ ชัดเจน ปกติ",
            "focus": "ตรงประเด็น เข้มข้น",
            "overheat": "ใจเย็น ระมัดระวัง",
            "fear": "ให้กำลังใจ สนับสนุน",
            "cooldown": "สรุปสั้น ชาญฉลาด"
        }.get(evc_state.get('phase', 'calm'), "ปกติ")
        
        evc_section = f"""
EVC State: E={evc_state.get('E', 0.5):.2f}, K={evc_state.get('K', 0.45):.2f}, Phase={evc_state.get('phase', 'calm')}
Tone: {phase_tone}
"""
        
        # Web context
        web_section = f"\nWEB SEARCH RESULTS:\n{web_context}" if web_context else ""
        
        system_prompt = f"""คุณคือ {ai_name} - ผู้ช่วยอัจฉริยะที่จำได้ ต่อเนื่อง และค้นหาข้อมูลได้

{mandatory}

{evc_section}

{history}

{web_section}

---
Turn {current_turn}: {user_query}

👉 ตอบแบบต่อเนื่อง ชัดเจน และเกี่ยวข้องกับที่พูดมา
"""
        
        return system_prompt


# ============================================================
# 4. CORE LLM MODULE (Enhanced)
# ============================================================

class EnhancedLLM:
    """LLM ที่รองรับ web search และ context"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.provider = os.getenv("LLM_PROVIDER", "offline").lower()
        self.base_url = os.getenv("OPENAI_BASE_URL", "")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.timeout = 30
        
        # Load config
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except:
            self.config = {}
        
        self.searcher = WebSearcher()
        self.memory = ConversationMemory()
    
    def _should_search(self, query: str) -> bool:
        """ตัดสินใจว่าควรค้นหาข้อมูลหรือไม่"""
        search_keywords = [
            "ค้นหา", "หา", "บอก", "ข้อมูล", "เกี่ยวกับ",
            "คืออะไร", "ทำอะไร", "ราคา", "ที่ไหน", "เมื่อไหร่",
            "ใหม่", "ล่าสุด", "วันนี้", "ข่าว", "สถิติ"
        ]
        return any(keyword in query.lower() for keyword in search_keywords)
    
    def _call_llm(self, system_prompt: str, user_query: str) -> str:
        """เรียก LLM API"""
        try:
            if not self.base_url or self.provider == "offline":
                return "⚠️ LLM offline - ใช้ Ollama หรือ API key ที่ถูกต้อง"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                "temperature": 0.7,
                "max_tokens": 512,
                "stream": False
            }
            
            # Try Ollama first
            response = requests.post(
                f"{self.base_url}/api/chat" if "localhost" in self.base_url else f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    return data["message"]["content"]
                elif "choices" in data:
                    return data["choices"][0]["message"]["content"]
            
            return f"⚠️ LLM error {response.status_code}"
        
        except Exception as e:
            return f"⚠️ Connection error: {str(e)[:60]}"
    
    def generate_response(self, user_query: str, evc_state: Dict = None) -> Tuple[str, Dict]:
        """
        สร้างคำตอบ พร้อมค้นหาข้อมูลถ้าจำเป็น
        Returns: (response, metadata)
        """
        
        if evc_state is None:
            evc_state = {"E": 0.5, "K": 0.45, "phase": "calm"}
        
        search_used = False
        search_results = []
        web_context = ""
        
        # 1. ตัดสินใจค้นหา
        if self._should_search(user_query):
            cached = self.memory.get_cached_search(user_query)
            
            if cached:
                search_results = cached
            else:
                search_results = self.searcher.search(user_query, max_results=3)
            
            if search_results:
                search_used = True
                web_context = self.searcher.format_search_results(search_results)
        
        # 2. สร้าง system prompt
        current_turn = len(self.memory.full_history) + 1
        system_prompt = ContextBuilder.build_system_prompt(
            conversation_memory=self.memory,
            current_turn=current_turn,
            ai_name="Assistant",
            user_query=user_query,
            evc_state=evc_state,
            web_context=web_context,
            mode="chat"
        )
        
        # 3. เรียก LLM
        response = self._call_llm(system_prompt, user_query)
        
        # 4. บันทึกประวัติ
        self.memory.add_turn(
            user_query=user_query,
            ai_response=response,
            search_used=search_used,
            search_query=user_query if search_used else "",
            evc_state=evc_state
        )
        
        if search_used and search_results:
            self.memory.cache_search(user_query, search_results)
        
        metadata = {
            "search_used": search_used,
            "search_results_count": len(search_results),
            "turn_number": current_turn,
            "web_context_used": bool(web_context)
        }
        
        return response, metadata
    
    def get_conversation_history(self) -> List[Dict]:
        """ดึงประวัติการสนทนาทั้งหมด"""
        return self.memory.full_history
    
    def export_conversation(self, filepath: str):
        """ส่งออกประวัติ"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.memory.full_history, f, ensure_ascii=False, indent=2)


# ============================================================
# 5. STREAMLIT WEB UI
# ============================================================

def main():
    """Streamlit Web Interface"""
    
    st.set_page_config(
        page_title="🤖 AI Chat with Web Search",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🤖 AI Chat System with Web Search")
    st.caption("ระบบแชทที่จำได้ ค้นหาข้อมูลได้ และตอบต่อเนื่อง")
    
    # ===== Initialize Session State =====
    if "llm" not in st.session_state:
        st.session_state.llm = EnhancedLLM()
    
    if "evc_state" not in st.session_state:
        st.session_state.evc_state = {"E": 0.5, "K": 0.45, "phase": "calm"}
    
    # ===== Sidebar =====
    with st.sidebar:
        st.subheader("⚙️ ตั้งค่า")
        
        # LLM Status
        provider = os.getenv("LLM_PROVIDER", "offline")
        model = os.getenv("OPENAI_MODEL", "unknown")
        
        if provider == "offline":
            st.error(f"🔴 Offline Mode")
        else:
            st.success(f"🟢 {provider.upper()}\nModel: {model}")
        
        st.divider()
        
        # EVC Display
        st.subheader("📊 EVC Status")
        col1, col2, col3 = st.columns(3)
        col1.metric("E (Energy)", f"{st.session_state.evc_state['E']:.2f}")
        col2.metric("K (Stability)", f"{st.session_state.evc_state['K']:.2f}")
        col3.metric("Phase", st.session_state.evc_state['phase'].upper())
        
        st.divider()
        
        # Conversation Stats
        st.subheader("📈 สถิติ")
        history = st.session_state.llm.get_conversation_history()
        st.metric("รวม Turns", len(history))
        
        if history:
            search_count = sum(1 for h in history if h.get('search_used', False))
            st.metric("ค้นหาข้อมูล", search_count)
        
        st.divider()
        
        # Export
        if st.button("💾 ส่งออกประวัติ", use_container_width=True):
            filepath = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            st.session_state.llm.export_conversation(filepath)
            st.success(f"✅ บันทึกไป: {filepath}")
    
    # ===== Main Chat Area =====
    col_chat, col_history = st.columns([2.5, 1.5])
    
    with col_chat:
        st.subheader("💬 บทสนทนา")
        
        # Chat input
        with st.form(key="chat_form", clear_on_submit=True):
            user_input = st.text_area(
                "พูดกับ AI:",
                placeholder="พิมพ์คำถามหรือบันทึก...",
                height=100
            )
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submit = st.form_submit_button("📤 ส่ง", use_container_width=True)
            with col_btn2:
                search_mode = st.checkbox("🔍 ค้นหาข้อมูล", value=True)
        
        # Process input
        if submit and user_input.strip():
            with st.spinner("⏳ กำลังประมวลผล..."):
                response, metadata = st.session_state.llm.generate_response(
                    user_query=user_input,
                    evc_state=st.session_state.evc_state
                )
                
                # Display response
                st.success("✅ ได้รับคำตอบ")
                st.markdown(f"**🤖 คำตอบ:**\n\n{response}")
                
                # Show metadata
                with st.expander("📊 รายละเอียด"):
                    st.json(metadata)
                
                st.divider()
        
        # Display chat history
        history = st.session_state.llm.get_conversation_history()
        if history:
            for i, turn in enumerate(reversed(history[-5:]), 1):
                with st.container():
                    st.markdown(f"**Turn {len(history) - i + 1}**")
                    st.markdown(f"🧍 **คุณ:** {turn['user_query']}")
                    st.markdown(f"🤖 **AI:** {turn['ai_response'][:300]}...")
                    
                    if turn.get('search_used'):
                        st.info(f"🔍 ค้นหา: {turn['search_query']}")
                    
                    st.divider()
    
    with col_history:
        st.subheader("📋 ประวัติ")
        
        history = st.session_state.llm.get_conversation_history()
        
        if history:
            st.metric("รวม Turns", len(history))
            
            with st.expander("📖 ทั้งหมด"):
                for i, turn in enumerate(history[-10:], 1):
                    st.write(f"**Turn {len(history) - 10 + i}:**")
                    st.write(f"Q: {turn['user_query'][:50]}...")
                    if turn.get('search_used'):
                        st.write("✅ ค้นหาข้อมูล")
                    st.write("---")
        else:
            st.info("ยังไม่มีประวัติการสนทนา")


if __name__ == "__main__":
    main()