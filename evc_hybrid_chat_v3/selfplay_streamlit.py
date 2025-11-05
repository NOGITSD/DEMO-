#!/usr/bin/env python3
"""
Integrated AI Self-Play Trainer for Streamlit Web UI
- Runs inline within web.py
- Uses Ollama (gpt-oss:120b-cloud)
- Real-time visualization + memory management
"""

import os
import json
import time
import yaml
from datetime import datetime
from typing import Dict, List, Any, Tuple
from collections import defaultdict

from evc_engine import EVCEngine
from reflection import reflect
from core_llm import get_llm_core
from memory import Memory

# ===================================================================
# AI Player Class (Integrated)
# ===================================================================
class AIPlayer:
    """Single AI player with EVC state tracking"""
    
    def __init__(self, name: str, cfg: Dict[str, Any]):
        self.name = name
        self.evc = EVCEngine(cfg)
        self.llm = get_llm_core()
        self.cfg = cfg
        self.conversation_log = []
        self.evc_states = []
        
    def reset(self):
        """Reset for new episode"""
        self.conversation_log = []
        self.evc_states = []
        self.evc.E = self.cfg["evc"]["E_init"]
        self.evc.K = self.cfg["evc"]["K"]
        
    def respond(self, prompt: str, mode: str = "chat", progress_callback=None) -> Tuple[str, Dict]:
        """Generate response based on current EVC state"""
        
        try:
            # Update EVC from prompt
            evc_info = self.evc.update_from_text(prompt)
            tone = self.evc.tone_from_phase(self.cfg.get("tone_map", {}))
            
            # Build system prompt
            if mode == "evc":
                system_prompt = f"""วิเคราะห์เป็น JSON ตามแนวคิด EVC (Energy-Value Conservation)
Tone: {tone}
ตอบเป็น JSON เท่านั้น"""
            else:
                system_prompt = f"""คุณเป็น AI ผู้ช่วยที่สนใจในการวิเคราะห์ตลาดและ EVC
Tone: {tone}
พูดภาษาไทยอย่างธรรมชาติและมีบริบท"""
            
            if progress_callback:
                progress_callback(f"🤖 {self.name} กำลังคิด... ({mode})")
            
            # Generate response
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
            
            # Check for errors
            if raw_response.startswith("⚠️"):
                response = f"ขอโทษครับ ขาดการเชื่อมต่อชั่วคราว ({self.name})"
            else:
                response = raw_response
            
            # Reflect on response
            try:
                rvec = reflect(prompt, response)
            except Exception as e:
                rvec = {
                    "coherence": 0.5,
                    "toxicity": 0.0,
                    "satisfaction": 0.5,
                    "verbosity": 0.5
                }
            
            # Update EVC from reflection
            evc_info2 = self.evc.update_from_reflection(rvec)
            
            # Save to log
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
            
            self.conversation_log.append(turn_data)
            self.evc_states.append(evc_info2)
            
            return response, turn_data
            
        except Exception as e:
            raise Exception(f"❌ {self.name} Error: {str(e)}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get player's conversation summary"""
        if not self.evc_states:
            return {
                "turns": 0,
                "avg_E": 0.5,
                "avg_K": 0.45,
                "max_E": 0.5,
                "min_E": 0.5,
                "phases": {},
                "final_phase": "calm"
            }
        
        e_values = [s.get("E", 0.5) for s in self.evc_states]
        k_values = [s.get("K", 0.45) for s in self.evc_states]
        phases = [s.get("phase", "calm") for s in self.evc_states]
        
        return {
            "turns": len(self.conversation_log),
            "avg_E": sum(e_values) / len(e_values),
            "avg_K": sum(k_values) / len(k_values),
            "max_E": max(e_values),
            "min_E": min(e_values),
            "phases": dict([(p, phases.count(p)) for p in set(phases)]),
            "final_phase": phases[-1] if phases else "calm"
        }


# ===================================================================
# Dual AI Conversation Engine
# ===================================================================
class DualConversation:
    """Manage dual AI conversation (A vs B)"""
    
    def __init__(self, cfg: Dict[str, Any], topic: str):
        self.cfg = cfg
        self.topic = topic
        self.player_a = AIPlayer("A", cfg)
        self.player_b = AIPlayer("B", cfg)
        self.episode_data = {
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "turns": []
        }
        self.turn_results = []
        
    def run_episode(self, max_turns: int = 6, 
                   mode_pattern: List[str] = None,
                   progress_container = None) -> Dict[str, Any]:
        """Run one full episode of dual conversation"""
        
        if mode_pattern is None:
            mode_pattern = ["chat", "evc", "chat", "evc", "chat", "evc"]
        
        def progress_cb(msg):
            if progress_container:
                progress_container.write(f"⏳ {msg}")
        
        # Initial prompt
        current_prompt = f"หัวข้อ: {self.topic}\nเริ่มการสนทนาแบบธรรมชาติครับ"
        players = [self.player_a, self.player_b]
        
        for turn_idx in range(min(max_turns, len(mode_pattern))):
            current_player = players[turn_idx % 2]
            other_player = players[(turn_idx + 1) % 2]
            mode = mode_pattern[turn_idx]
            
            try:
                # Get response
                response, turn_data = current_player.respond(
                    current_prompt, 
                    mode=mode,
                    progress_callback=progress_cb
                )
                
                # Rate response
                rating = self._rate_response(response, turn_data)
                
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
                    "rating": rating,
                    "timestamp": datetime.now().isoformat()
                }
                
                self.episode_data["turns"].append(turn_info)
                self.turn_results.append(turn_info)
                
                progress_cb(
                    f"✓ Turn {turn_idx + 1}: {current_player.name} "
                    f"[E={turn_data['evc_after']['E']:.2f} "
                    f"Phase={turn_data['evc_after']['phase']}]"
                )
                
                # Next prompt
                current_prompt = response
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                progress_cb(f"⚠️ Turn {turn_idx + 1} Error: {str(e)[:100]}")
                continue
        
        # Finalize
        self.episode_data["summary"] = {
            "total_turns": len(self.episode_data["turns"]),
            "player_a": self.player_a.get_summary(),
            "player_b": self.player_b.get_summary()
        }
        
        return self.episode_data
    
    def _rate_response(self, response: str, turn_data: Dict) -> Dict[str, float]:
        """Rate AI response quality"""
        reflection = turn_data["reflection"]
        evc = turn_data["evc_after"]
        
        clarity = min(1.0, len(response) / 500) * (1 - reflection.get("toxicity", 0))
        coherence = reflection.get("coherence", 0.5)
        phase_bonus = {"focus": 1.2, "overheat": 0.8, "fear": 0.7}.get(evc["phase"], 1.0)
        engagement = min(1.0, reflection.get("satisfaction", 0.5) * phase_bonus)
        
        return {
            "clarity": float(clarity),
            "coherence": float(coherence),
            "engagement": float(engagement),
            "overall": float((clarity + coherence + engagement) / 3)
        }


# ===================================================================
# Training Data Manager
# ===================================================================
class TrainingDataManager:
    """Manage training data generation and storage"""
    
    def __init__(self, output_dir: str = "data"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.training_file = os.path.join(output_dir, "selfplay_training.jsonl")
        self.memory_file = os.path.join(output_dir, "selfplay_memory.json")
        self.sample_count = 0
        
    def save_episode(self, episode: Dict) -> int:
        """Save episode as training samples, return count"""
        count = 0
        
        for turn in episode["turns"]:
            sample = {
                "instruction": "ตอบคำพูดถัดไปในการสนทนาตลาด EVC อย่างธรรมชาติและน่าสนใจ",
                "input": turn["prompt"],
                "output": turn["response"],
                "topic": episode["topic"],
                "mode": turn["mode"],
                "speaker": turn["speaker"],
                "evc_state": turn["evc_speaker"],
                "reflection": turn["reflection"],
                "rating": turn["rating"],
                "turn_number": turn["turn"],
                "timestamp": turn["timestamp"]
            }
            
            with open(self.training_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
            
            count += 1
            self.sample_count += 1
        
        return count
    
    def save_memory(self, episodes: List[Dict], metadata: Dict = None) -> None:
        """Save full memory with all episodes"""
        memory = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_samples": self.sample_count,
                "training_file": self.training_file,
                **(metadata or {})
            },
            "episodes": episodes
        }
        
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)


# ===================================================================
# Streamlit Integration Functions
# ===================================================================
def run_selfplay_session(
    num_episodes: int = 3,
    max_turns_per_episode: int = 6,
    topics: List[str] = None,
    st_placeholder = None
) -> Tuple[List[Dict], Dict]:
    """
    Run self-play training session (callable from Streamlit)
    
    Returns:
        (episodes_list, statistics_dict)
    """
    
    # Load config
    cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
    
    if topics is None:
        topics = [
            "อภิปรายข้อดีข้อเสียของ AI ในการเทรดหุ้น",
            "วิเคราะห์สถานะตลาด EVC ปัจจุบัน",
            "ทำไม NVDA ถึงเป็น Tech Stock ยอดนิยม"
        ]
    
    # Initialize
    trainer = TrainingDataManager()
    all_episodes = []
    stats = {
        "total_episodes": num_episodes,
        "completed": 0,
        "failed": 0,
        "total_turns": 0,
        "total_samples": 0,
        "avg_ratings": {}
    }
    
    # Status container
    status_col = st_placeholder if st_placeholder else None
    
    for ep_idx in range(num_episodes):
        topic = topics[ep_idx % len(topics)]
        ep_name = f"Episode {ep_idx + 1}/{num_episodes}"
        
        if status_col:
            status_col.info(f"🟢 {ep_name}: {topic}")
        
        try:
            # Run conversation
            conv = DualConversation(cfg, topic)
            episode = conv.run_episode(
                max_turns=max_turns_per_episode,
                mode_pattern=["chat", "evc", "chat", "evc", "chat", "evc"][:max_turns_per_episode],
                progress_container=status_col
            )
            
            # Save training data
            samples = trainer.save_episode(episode)
            all_episodes.append(episode)
            
            # Update stats
            stats["completed"] += 1
            stats["total_turns"] += episode["summary"]["total_turns"]
            stats["total_samples"] += samples
            
            if status_col:
                status_col.success(
                    f"✅ {ep_name} สำเร็จ: {samples} samples | "
                    f"Turns: {episode['summary']['total_turns']}"
                )
            
        except Exception as e:
            stats["failed"] += 1
            if status_col:
                status_col.error(f"❌ {ep_name} Error: {str(e)[:100]}")
    
    # Save memory
    trainer.save_memory(
        all_episodes,
        metadata={
            "completed_episodes": stats["completed"],
            "failed_episodes": stats["failed"],
            "total_turns": stats["total_turns"],
            "total_samples": stats["total_samples"]
        }
    )
    
    stats["training_file"] = trainer.training_file
    stats["memory_file"] = trainer.memory_file
    
    return all_episodes, stats