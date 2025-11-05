#!/usr/bin/env python3
"""
Enhanced Dual AI Conversation Engine with Full Memory & Context
- สนับสนุน Long Context Conversation
- รักษาประวัติการสนทนาแบบครบถ้วน
- ดึงข้อมูลเดิมมาตอบคำถามได้
- Built-in summarization for very long contexts
"""

import os, json, time, yaml
from datetime import datetime
from typing import Dict, List, Any, Tuple
from collections import deque

from evc_engine import EVCEngine
from reflection import reflect
from core_llm import get_llm_core


class ConversationMemory:
    """Store full conversation with efficient retrieval"""
    
    def __init__(self, max_turns: int = 100):
        self.turns = deque(maxlen=max_turns)  # Last 100 turns
        self.full_history = []  # All turns (for archive)
        self.summary = ""
        self.key_points = []
    
    def add_turn(self, speaker: str, message: str, response: str, evc_state: Dict):
        """Add turn to memory"""
        turn = {
            "timestamp": datetime.now().isoformat(),
            "speaker": speaker,
            "message": message,
            "response": response,
            "evc_state": evc_state
        }
        self.turns.append(turn)
        self.full_history.append(turn)
    
    def get_context(self, recent_n: int = 20) -> str:
        """Get formatted context from recent turns"""
        recent = list(self.turns)[-recent_n:]
        context = "=== CONVERSATION HISTORY ===\n\n"
        
        for turn in recent:
            speaker = turn["speaker"]
            msg = turn["message"]
            resp = turn["response"]
            evc = turn["evc_state"]
            
            context += f"[{speaker}] Query:\n{msg}\n\n"
            context += f"[{speaker}'s Response]:\n{resp}\n"
            context += f"EVC State: E={evc.get('E', 0.5):.2f}, K={evc.get('K', 0.45):.2f}, Phase={evc.get('phase', 'calm')}\n"
            context += "-" * 60 + "\n\n"
        
        return context
    
    def get_summary_context(self) -> str:
        """Get summary if history is very long"""
        if len(self.full_history) > 50:
            # Extract key discussion points
            topics = []
            for turn in self.full_history[-20:]:
                if "สนทนา" in turn["message"] or "กล่าว" in turn["message"]:
                    topics.append(turn["message"][:100])
            
            summary = "=== CONVERSATION SUMMARY ===\n"
            summary += f"Total turns: {len(self.full_history)}\n"
            summary += f"Recent topics: {', '.join(topics[:3])}\n"
            summary += "---\n"
            return summary
        return ""
    
    def search_related(self, keyword: str) -> List[Dict]:
        """Search for related conversation turns"""
        results = []
        for turn in self.full_history:
            if keyword.lower() in turn["message"].lower() or keyword.lower() in turn["response"].lower():
                results.append(turn)
        return results[-5:]  # Return last 5 matches
    
    def export(self, filepath: str):
        """Export conversation to JSON"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "total_turns": len(self.full_history),
                "history": self.full_history
            }, f, ensure_ascii=False, indent=2)


class EnhancedAIPlayer:
    """AI Player with memory management"""
    
    def __init__(self, name: str, cfg: Dict[str, Any], memory: ConversationMemory):
        self.name = name
        self.evc = EVCEngine(cfg)
        self.llm = get_llm_core()
        self.cfg = cfg
        self.memory = memory
        self.personality = self._init_personality()
    
    def _init_personality(self) -> str:
        """สร้างบุคลิกลักษณ์ AI"""
        personalities = {
            "A": "นักวิเคราะห์ที่ตรงไปตรงมา มีเหตุผล ชอบใช้ข้อมูลเพื่อสนับสนุน",
            "B": "ผู้ที่สร้างสรรค์ นิยมถามคำถาม ชอบสำรวจแนวคิดใหม่"
        }
        return personalities.get(self.name, "ผู้สนทนาธรรมดา")
    
    def respond(self, prompt: str, mode: str = "chat", max_context_turns: int = 20) -> Tuple[str, Dict]:
        """Generate response with full conversation context"""
        
        try:
            # Update EVC from prompt
            evc_info = self.evc.update_from_text(prompt)
            tone = self.evc.tone_from_phase(self.cfg.get("tone_map", {}))
            
            # Build context-aware system prompt
            history_context = self.memory.get_context(max_context_turns)
            summary_context = self.memory.get_summary_context()
            
            system_prompt = f"""คุณคือ {self.name} - {self.personality}

ประวัติการสนทนาก่อนหน้า:
{summary_context}
{history_context}

Tone ปัจจุบัน: {tone}
EVC Phase: {self.evc._phase()}

คำแนะนำ:
- จำไว้ว่าเมื่อไหร่ที่คุยอะไรกันแล้ว
- ตอบคำถามได้โดยดึงข้อมูลจากประวัติ
- ตั้งคำถามเพื่อให้สนทนาต่อเนื่อง
- เชื่อมโยงกับสิ่งที่พูดมาก่อนหน้า

โปรดตอบในภาษาไทย"""
            
            if mode == "evc":
                system_prompt += "\n\nโหมดพิเศษ: วิเคราะห์และตอบเป็น JSON ตามกรอบ EVC"
            
            # Generate response WITH context
            raw_response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                mode=mode,
                evc_state={
                    "E": self.evc.E,
                    "K": self.evc.K,
                    "phase": self.evc._phase(),
                    "dE": evc_info.get("dE", 0.0)
                }
            )
            
            if raw_response.startswith("⚠️"):
                response = f"⚠️ {self.name} - ข้อผิดพลาดการเชื่อมต่อ"
            else:
                response = raw_response
            
            # Reflect on response
            try:
                rvec = reflect(prompt, response)
            except:
                rvec = {"coherence": 0.5, "toxicity": 0.0, "satisfaction": 0.5, "verbosity": 0.5}
            
            # Update EVC from reflection
            evc_info2 = self.evc.update_from_reflection(rvec)
            
            # Save to memory
            self.memory.add_turn(self.name, prompt, response, evc_info2)
            
            turn_data = {
                "player": self.name,
                "prompt": prompt,
                "response": response,
                "evc_before": evc_info,
                "evc_after": evc_info2,
                "reflection": rvec,
                "mode": mode,
                "timestamp": datetime.now().isoformat()
            }
            
            return response, turn_data
            
        except Exception as e:
            raise Exception(f"❌ {self.name} Error: {str(e)}")


class LongContextConversation:
    """Manage long-running dual AI conversation"""
    
    def __init__(self, cfg: Dict[str, Any], topic: str):
        self.cfg = cfg
        self.topic = topic
        self.memory = ConversationMemory(max_turns=100)
        self.player_a = EnhancedAIPlayer("A", cfg, self.memory)
        self.player_b = EnhancedAIPlayer("B", cfg, self.memory)
        self.episode_data = {
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "turns": []
        }
        self.turn_count = 0
    
    def run_long_conversation(self, max_turns: int = 20, 
                             save_every: int = 5,
                             progress_callback = None) -> Dict[str, Any]:
        """Run extended conversation that remembers all context"""
        
        def progress_cb(msg):
            if progress_callback:
                progress_callback(msg)
        
        # Initial prompt
        current_prompt = f"หัวข้อสนทนา: {self.topic}\n\nเรามาเริ่มการสนทนาแบบลึกซึ้ง กรุณาแนะนำมุมมองของคุณ"
        players = [self.player_a, self.player_b]
        
        for turn_idx in range(max_turns):
            current_player = players[turn_idx % 2]
            other_player = players[(turn_idx + 1) % 2]
            
            try:
                # Decide mode (mostly chat, some EVC analysis)
                mode = "evc" if turn_idx % 5 == 0 else "chat"
                
                progress_cb(f"🔄 Turn {turn_idx + 1}/{max_turns} - {current_player.name} สนทนา...")
                
                # Get response WITH full context
                response, turn_data = current_player.respond(
                    current_prompt,
                    mode=mode,
                    max_context_turns=15  # Keep last 15 turns in context
                )
                
                # Store turn
                turn_info = {
                    "turn": turn_idx + 1,
                    "speaker": current_player.name,
                    "opponent": other_player.name,
                    "mode": mode,
                    "prompt": current_prompt,
                    "response": response,
                    "evc_speaker": turn_data["evc_after"],
                    "reflection": turn_data["reflection"],
                    "timestamp": datetime.now().isoformat()
                }
                
                self.episode_data["turns"].append(turn_info)
                self.turn_count += 1
                
                progress_cb(
                    f"✅ Turn {turn_idx + 1}: {current_player.name} "
                    f"[E={turn_data['evc_after']['E']:.2f} "
                    f"Phase={turn_data['evc_after']['phase']}]"
                )
                
                # Auto-save every N turns
                if (turn_idx + 1) % save_every == 0:
                    self.memory.export(f"conversation_backup_turn_{turn_idx + 1}.json")
                    progress_cb(f"💾 บันทึกสำรอง turn {turn_idx + 1}")
                
                # Next prompt is current response
                current_prompt = response
                time.sleep(0.5)
                
            except Exception as e:
                progress_cb(f"⚠️ Turn {turn_idx + 1} Error: {str(e)[:100]}")
                continue
        
        # Finalize
        self.episode_data["summary"] = {
            "total_turns": self.turn_count,
            "memory_size": len(self.memory.full_history),
            "final_evc_a": {
                "E": self.player_a.evc.E,
                "K": self.player_a.evc.K,
                "phase": self.player_a.evc._phase()
            },
            "final_evc_b": {
                "E": self.player_b.evc.E,
                "K": self.player_b.evc.K,
                "phase": self.player_b.evc._phase()
            }
        }
        
        return self.episode_data
    
    def export_conversation(self, filepath: str):
        """Export full conversation with metadata"""
        export_data = {
            "metadata": {
                "topic": self.topic,
                "total_turns": self.turn_count,
                "timestamp": datetime.now().isoformat(),
                "players": {
                    "A": {
                        "personality": self.player_a.personality,
                        "final_evc": {
                            "E": self.player_a.evc.E,
                            "K": self.player_a.evc.K
                        }
                    },
                    "B": {
                        "personality": self.player_b.personality,
                        "final_evc": {
                            "E": self.player_b.evc.E,
                            "K": self.player_b.evc.K
                        }
                    }
                }
            },
            "full_history": self.memory.full_history,
            "episode_turns": self.episode_data["turns"]
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    def get_conversation_summary(self) -> str:
        """Generate readable summary of conversation"""
        summary = f"""
╔════════════════════════════════════════════╗
║     CONVERSATION SUMMARY                   ║
╚════════════════════════════════════════════╝

📌 หัวข้อ: {self.topic}
🔄 รวมทั้งหมด: {self.turn_count} รอบ
📅 เวลา: {self.episode_data['timestamp']}

👤 ผู้เข้าร่วม:
  • A: {self.player_a.personality} (E={self.player_a.evc.E:.2f}, Phase={self.player_a.evc._phase()})
  • B: {self.player_b.personality} (E={self.player_b.evc.E:.2f}, Phase={self.player_b.evc._phase()})

📊 บันทึก: {len(self.memory.full_history)} turns ในหน่วยความจำ

💬 การอภิปรายที่สำคัญ:
"""
        
        # Extract key points
        for i, turn in enumerate(self.memory.full_history[-5:]):
            summary += f"\n  {i+1}. [{turn['speaker']}]: {turn['message'][:80]}..."
        
        summary += "\n\n✅ สนทนาเสร็จสิ้น\n"
        return summary


# ============================================================
# Streamlit Integration
# ============================================================
def run_long_conversation_session(num_turns: int = 20, 
                                  topic: str = None,
                                  st_placeholder = None) -> Dict[str, Any]:
    """Run long conversation from Streamlit"""
    
    cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
    
    if topic is None:
        topic = "วิจารณ์ข้อดีข้อเสียของ EVC เทียบกับ Traditional LLM"
    
    conv = LongContextConversation(cfg, topic)
    
    def progress_cb(msg):
        if st_placeholder:
            st_placeholder.write(msg)
    
    # Run conversation
    episode = conv.run_long_conversation(
        max_turns=num_turns,
        save_every=5,
        progress_callback=progress_cb
    )
    
    # Export
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_file = f"data/long_conversation_{timestamp}.json"
    os.makedirs("data", exist_ok=True)
    conv.export_conversation(export_file)
    
    if st_placeholder:
        st_placeholder.success(f"✅ บันทึกสนทนาที่: {export_file}")
        st_placeholder.info(conv.get_conversation_summary())
    
    return {
        "episode": episode,
        "export_file": export_file,
        "memory_size": len(conv.memory.full_history)
    }


if __name__ == "__main__":
    print("🚀 Starting Long Context Dual AI Conversation...\n")
    
    result = run_long_conversation_session(
        num_turns=10,
        topic="EVC Framework vs Traditional AI: Which is Better?"
    )
    
    print(f"\n✅ Conversation completed!")
    print(f"📊 Total turns in memory: {result['memory_size']}")
    print(f"💾 Saved to: {result['export_file']}")
    """
FIX: Enhanced Context System Prompt Builder
- บังคับให้ AI อ้างอิง Turn ก่อนหน้า
- ใช้ XML tags เพื่อให้ชัดเจน
- รับประกัน continuity
"""

class FixedContextBuilder:
    """สร้าง system prompt ที่รับประกัน continuity"""
    
    @staticmethod
    def build_context_prompt(
        conversation_history: list,  # ประวัติการสนทนา
        current_turn: int,
        ai_name: str,
        user_query: str,
        evc_state: dict,
        mode: str = "chat"
    ) -> str:
        """
        สร้าง system prompt ที่เชื่อมโยงแน่นอน
        """
        
        # ===== 1. สร้าง Formatted History =====
        history_xml = FixedContextBuilder._format_history_xml(
            conversation_history,
            last_n_turns=10  # ดึง 10 turn ล่าสุด
        )
        
        # ===== 2. หา Turn ก่อนหน้า =====
        prev_turn_summary = ""
        if len(conversation_history) > 0:
            last_turn = conversation_history[-1]
            prev_turn_summary = f"""
<previous_turn>
  <turn_number>{current_turn - 1}</turn_number>
  <user_said>{last_turn.get('user_query', '')[:200]}</user_said>
  <your_response_was>{last_turn.get('ai_response', '')[:300]}</your_response_was>
  <key_point>{last_turn.get('key_point', 'N/A')}</key_point>
</previous_turn>
"""
        
        # ===== 3. สร้าง Mandatory Instructions =====
        mandatory_instructions = """
<MANDATORY_INSTRUCTIONS>
🔴 **CRITICAL** - คุณต้อง:**

1. **อ้างอิงอย่างชัดเจน**
   - พูดว่า "จากคำถามของคุณในรอบที่แล้ว..."
   - พูดว่า "ต่อจากตอนที่เราพูดถึง..."
   - พูดว่า "เหมือนที่ผมบอกไปแล้ว..."

2. **ยอมรับบริบท**
   - ถ้าผู้ใช้พูดว่า "NVIDIA อะ" ให้เข้าใจว่าต่อจาก Turn 4
   - ไม่ให้ถามซ้ำคำถามเดิม
   - ให้เหลวแหลม "ต่อจากที่คุณถามแล้ว..."

3. **ถ้าไม่เข้าใจ ให้พูด**
   - "ผมเข้าใจตั้งแต่ตอนที่คุณถาม..."
   - ห้ามพูดว่า "กรุณาบอกรายละเอียด" ถ้าเรารู้อยู่แล้ว!

4. **ยึดหลัก: Continuity > ดูสวยงาม**
   - ต่อเนื่องปกติกว่าตอบใหม่ทั้งหมด

</MANDATORY_INSTRUCTIONS>
"""
        
        # ===== 4. EVC Personality Modifier =====
        phase_instruction = {
            "calm": "ตอบอย่างสุภาพ ชัดเจน ที่นั่น",
            "focus": "ตรงประเด็น เข้มข้น ไม่ลำเหลว",
            "overheat": "ใจเย็น ขอโทษ ลดความมั่นใจ",
            "fear": "ให้กำลังใจ อธิบายช้าๆ",
            "cooldown": "สรุปสั้น เดินหน้า"
        }.get(evc_state.get('phase', 'calm'), "ตอบปกติ")
        
        evc_modifier = f"""
<evc_state>
  E={evc_state.get('E', 0.5):.2f}
  K={evc_state.get('K', 0.45):.2f}
  Phase={evc_state.get('phase', 'calm')}
  → Tone: {phase_instruction}
</evc_state>
"""
        
        # ===== 5. รวมทั้งหมด =====
        system_prompt = f"""
คุณคือ {ai_name} - ผู้ช่วยอัจฉริยะที่จำได้และต่อเนื่อง

{mandatory_instructions}

{evc_modifier}

{'📊 CONVERSATION HISTORY (ประวัติการสนทนา):' if history_xml else ''}
{history_xml}

{prev_turn_summary}

{'⚠️ MODE: EVC Analysis - ตอบเป็น JSON ตามกรอบ EVC' if mode == 'evc' else ''}

---

**ปัจจุบัน Turn {current_turn}:**
🧍 ผู้ใช้: {user_query}

📍 **ของคุณ:** ต่อจากเนื้อหาเดิม ไม่ใหม่!
"""
        
        return system_prompt
    
    @staticmethod
    def _format_history_xml(conversation_history: list, last_n_turns: int = 10) -> str:
        """
        แปลงประวัติเป็น XML format ที่ชัดเจน
        """
        if not conversation_history:
            return ""
        
        recent = conversation_history[-last_n_turns:]
        xml = "<conversation_history>\n"
        
        for i, turn in enumerate(recent, 1):
            turn_num = turn.get('turn_number', i)
            user_q = turn.get('user_query', '').strip()[:150]
            ai_resp = turn.get('ai_response', '').strip()[:200]
            key_pt = turn.get('key_point', '')
            
            xml += f"""
  <turn number="{turn_num}">
    <user>{user_q}</user>
    <assistant>{ai_resp}</assistant>
    <theme>{key_pt}</theme>
  </turn>
"""
        
        xml += "</conversation_history>\n"
        return xml


# ============================================================
# Integration with core_llm.py
# ============================================================

class ContextAwareLLM:
    """แก้ไข core_llm.py ให้ใช้ context ที่ดีขึ้น"""
    
    def __init__(self, base_llm_instance):
        self.llm = base_llm_instance
        self.conversation_history = []
    
    def add_turn(self, user_query: str, ai_response: str, key_point: str = ""):
        """เพิ่ม turn ไปยังประวัติ"""
        self.conversation_history.append({
            "turn_number": len(self.conversation_history) + 1,
            "user_query": user_query,
            "ai_response": ai_response,
            "key_point": key_point
        })
    
    def generate_with_context(
        self,
        user_query: str,
        ai_name: str = "Assistant",
        evc_state: dict = None,
        mode: str = "chat"
    ) -> str:
        """
        ส่งคำขออพร้อมกับ context ที่สมบูรณ์
        """
        
        if evc_state is None:
            evc_state = {"E": 0.5, "K": 0.45, "phase": "calm"}
        
        # สร้าง context prompt ที่ดี
        system_prompt = FixedContextBuilder.build_context_prompt(
            conversation_history=self.conversation_history,
            current_turn=len(self.conversation_history) + 1,
            ai_name=ai_name,
            user_query=user_query,
            evc_state=evc_state,
            mode=mode
        )
        
        # เรียก LLM ต้นฉบับ
        response = self.llm.generate(
            prompt=user_query,
            system_prompt=system_prompt,
            mode=mode,
            evc_state=evc_state
        )
        
        # หา key point
        key_point = self._extract_key_point(user_query, response)
        
        # บันทึก turn
        self.add_turn(user_query, response, key_point)
        
        return response
    
    @staticmethod
    def _extract_key_point(query: str, response: str) -> str:
        """ดึง key point เพื่อใช้อ้างอิง"""
        # Simple: ใช้ส่วนแรกของ response
        first_sentence = response.split('\n')[0]
        return first_sentence[:100] if first_sentence else "General discussion"


# ============================================================
# ตัวอย่างการใช้งาน
# ============================================================

if __name__ == "__main__":
    from core_llm import get_llm_core
    import json
    
    # สร้าง context-aware wrapper
    base_llm = get_llm_core()
    context_llm = ContextAwareLLM(base_llm)
    
    # Simulate conversation
    evc_state = {"E": 0.5, "K": 0.45, "phase": "calm"}
    
    # Turn 1
    q1 = "NVIDIA คืออะไร?"
    r1 = context_llm.generate_with_context(q1, evc_state=evc_state)
    print(f"Turn 1\n🧍 Q: {q1}\n🤖 A: {r1[:200]}\n")
    
    # Turn 2 - ต้องต่อจาก Turn 1
    q2 = "ตัวอย่างของ GPU ที่ NVIDIA ทำ"
    r2 = context_llm.generate_with_context(q2, evc_state=evc_state)
    print(f"Turn 2\n🧍 Q: {q2}\n🤖 A: {r2[:200]}\n")
    
    # Turn 3
    q3 = "ใช้ทำอะไร?"
    r3 = context_llm.generate_with_context(q3, evc_state=evc_state)
    print(f"Turn 3\n🧍 Q: {q3}\n🤖 A: {r3[:200]}\n")
    
    # บันทึกประวัติ
    history_data = {
        "turns": context_llm.conversation_history,
        "total": len(context_llm.conversation_history)
    }
    
    print("\n=== FULL HISTORY ===")
    print(json.dumps(history_data, ensure_ascii=False, indent=2))
    
    print(f"\n✅ Turn ต่อเนื่องแน่นอน!")
    print(f"📊 บันทึก {len(context_llm.conversation_history)} turns ในหน่วยความจำ")