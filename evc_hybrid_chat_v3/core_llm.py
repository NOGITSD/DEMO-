"""
core_llm.py - Enhanced LLM Core for web.py Integration
- Works seamlessly with web.py
- Support EVC context
- Better error handling
"""

import os
import json
import requests
import datetime
import traceback
import re
from typing import Dict, Any, Optional, Tuple

class LLMCore:
    """Enhanced LLM Wrapper with EVC context awareness"""
    
    EVC_CONTEXT = """
=== EVC (Energy Value Conservation) Framework ===
ระบบวิเคราะห์อารมณ์และพลังงานของ AI โดยติดตามพารามิเตอร์หลัก:

**ตัวแปรหลัก:**
- E (Energy): ระดับพลังงาน/ความมั่นใจ (0.0-1.5)
  * ต่ำ (0-0.25) = Fear phase
  * กลาง (0.25-0.75) = Calm/Focus phase
  * สูง (0.75+) = Overheat phase
  
- K (Stability/Sensitivity): ความเสถียรของระบบ (0.25-0.75)
  * K สูง = เสถียร, ตอบสนองช้า
  * K ต่ำ = ไม่เสถียร, ตอบสนองรวดเร็ว
  
- ΔE (Change): การเปลี่ยนแปลงของพลังงาน

**Phase (ระยะ):**
- calm: เชื่อมั่นปกติ
- focus: มั่นใจสูง ตรงประเด็น
- overheat: พลังงานสูงเกินไป ต้องระมัดระวัง
- fear: กลัว/ไม่แน่ใจ ต้องให้กำลังใจ
- cooldown: ปรับตัวกลับสู่สมดุล
"""
    
    def __init__(self):
        """Initialize LLM Core"""
        self.provider = os.getenv("LLM_PROVIDER", "offline").lower()
        self.base_url = self._normalize_url(os.getenv("OPENAI_BASE_URL", ""))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.timeout = 30
        self.debug = os.getenv("DEBUG_LOG", "true").lower() == "true"
        self.is_cloud = self._detect_cloud_provider()
        self.evc_state = {"E": 0.5, "K": 0.45, "phase": "calm"}
        self._log(f"🚀 LLM Core initialized - Provider: {self.provider}, Model: {self.model}")
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL"""
        if not url:
            return ""
        url = re.sub(r"/+$", "", url.strip())
        url = re.sub(r"/(v1|api)$", "", url)
        return url
    
    def _is_local(self, url: str) -> bool:
        """Check if URL is local"""
        return "localhost" in url or "127.0.0.1" in url
    
    def _detect_cloud_provider(self) -> bool:
        """Detect if using cloud provider"""
        cloud_indicators = ["cloud", "gpt-oss", "openai", "together", "replicate", "huggingface"]
        return any(indicator in self.model.lower() for indicator in cloud_indicators)
    
    def _log(self, msg: str):
        """Log message"""
        if self.debug:
            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
            print(f"[LLMCore:{timestamp}] {msg}")
    
    def set_evc_state(self, evc_state: Dict[str, Any]):
        """Set EVC state for current session"""
        self.evc_state = evc_state
        self._log(f"✓ EVC State: E={evc_state.get('E', 0.5):.2f}, K={evc_state.get('K', 0.45):.2f}, Phase={evc_state.get('phase', 'calm')}")
    
    def _build_evc_system_prompt(self, system_prompt: str, mode: str) -> str:
        """Build system prompt with EVC context"""
        
        evc_info = f"""
** EVC Current State **
- Energy (E): {self.evc_state.get('E', 0.5):.2f}
- Stability (K): {self.evc_state.get('K', 0.45):.2f}
- Phase: {self.evc_state.get('phase', 'calm')}
- Last ΔE: {self.evc_state.get('dE', 0.0):.2f}
"""
        
        if mode == "evc":
            evc_prompt = self.EVC_CONTEXT + evc_info + """
Task: วิเคราะห์ข้อมูลและตอบเป็น JSON พร้อมการประเมิน EVC:
{
  "E": <ตัวเลข>,
  "K": <ตัวเลข>,
  "Phase": "<phase>",
  "Meaning": "<คำอธิบาย>"
}"""
            return evc_prompt
        else:
            combined_prompt = system_prompt + evc_info
            return combined_prompt
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from response"""
        if not text or not isinstance(text, str):
            return text
        
        cleaned = re.sub(r'```(?:json)?\s*', '', text)
        cleaned = cleaned.strip()
        
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, cleaned, re.DOTALL)
        
        for match in matches:
            try:
                json.loads(match)
                return match
            except:
                continue
        
        return text
    
    def _call_ollama(self, prompt: str, system_prompt: str, mode: str) -> str:
        """Call Ollama API"""
        try:
            self._log(f"📡 Ollama call: Model={self.model}, Mode={mode}")
            
            full_system_prompt = self._build_evc_system_prompt(system_prompt, mode)
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": full_system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
            
            endpoint = f"{self.base_url}/api/chat"
            self._log(f"Trying: {endpoint}")
            
            response = requests.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                self._log(f"❌ Ollama error: {response.status_code}")
                return f"⚠️ Ollama Error {response.status_code}"
            
            data = response.json()
            content = data.get("message", {}).get("content", str(data))
            
            if not content:
                self._log(f"⚠️ Empty response from Ollama")
                return "⚠️ Empty response"
            
            self._log(f"✅ Ollama success")
            
            if mode == "evc":
                return self._extract_json(content)
            return content
        
        except requests.Timeout:
            self._log(f"⏱️ Ollama timeout")
            return "⚠️ Ollama Timeout"
        except Exception as e:
            self._log(f"❌ Ollama error: {str(e)[:80]}")
            return f"⚠️ Connection Error: {str(e)[:60]}"
    
    def _call_cloud_api(self, prompt: str, system_prompt: str, mode: str) -> str:
        """Call Cloud API (OpenAI-compatible)"""
        try:
            self._log(f"☁️ Cloud API call: Model={self.model}, Mode={mode}")
            
            if not self.base_url:
                return self._fallback_response(mode)
            
            full_system_prompt = self._build_evc_system_prompt(system_prompt, mode)
            
            headers = {
                "Content-Type": "application/json",
            }
            
            if self.api_key and self.api_key != "dummy-key":
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": full_system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 512,
                "stream": False
            }
            
            endpoint_urls = [
                f"{self.base_url}/v1/chat/completions",
                f"{self.base_url}/chat/completions",
                f"{self.base_url}/api/chat",
            ]
            
            for endpoint_url in endpoint_urls:
                try:
                    self._log(f"Trying: {endpoint_url}")
                    response = requests.post(
                        endpoint_url,
                        json=payload,
                        headers=headers,
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        content = None
                        
                        if "choices" in data:
                            content = data["choices"][0].get("message", {}).get("content")
                        elif "message" in data:
                            content = data.get("message", {}).get("content")
                        elif "response" in data:
                            content = data.get("response")
                        else:
                            content = str(data)
                        
                        if not content:
                            self._log(f"⚠️ Empty response")
                            continue
                        
                        self._log(f"✅ Cloud API success: {endpoint_url}")
                        
                        if mode == "evc":
                            return self._extract_json(content)
                        return content
                    
                    elif response.status_code == 404:
                        continue
                    else:
                        self._log(f"Status {response.status_code}")
                        continue
                
                except requests.Timeout:
                    self._log(f"⏱️ Timeout")
                    continue
                except Exception as e:
                    self._log(f"Error: {str(e)[:80]}")
                    continue
            
            return self._fallback_response(mode)
        
        except Exception as e:
            self._log(f"☁️ Cloud API error: {str(e)}")
            return self._fallback_response(mode)
    
    def _fallback_response(self, mode: str) -> str:
        """Fallback response when API fails"""
        if mode == "evc":
            return json.dumps({
                "E": self.evc_state.get('E', 5.0),
                "K": self.evc_state.get('K', 5.0),
                "dE": 0.0,
                "Phase": self.evc_state.get('phase', "calm"),
                "Meaning": "Offline mode"
            }, ensure_ascii=False)
        return "⚠️ ไม่สามารถเชื่อมต่อ LLM ได้ กรุณาตรวจสอบการเชื่อมต่อ"
    
    def generate(self, prompt: str, system_prompt: str = "", mode: str = "chat", evc_state: Dict = None) -> str:
        """
        Generate response with EVC context
        
        Args:
            prompt: User query
            system_prompt: System instructions
            mode: "chat" or "evc"
            evc_state: EVC state dict
        
        Returns:
            Generated response
        """
        
        if evc_state:
            self.set_evc_state(evc_state)
        
        if not system_prompt:
            system_prompt = "You are a helpful assistant. Respond in Thai language."
        
        self._log(f"Generate: Mode={mode}, Provider={self.provider}, IsCloud={self.is_cloud}")
        
        if self.provider == "offline" or not self.base_url:
            return self._fallback_response(mode)
        
        if self._is_local(self.base_url) or self.provider == "ollama":
            return self._call_ollama(prompt, system_prompt, mode)
        
        return self._call_cloud_api(prompt, system_prompt, mode)


# ============================================================
# SINGLETON & BACKWARD COMPATIBILITY
# ============================================================

_llm_instance = None

def get_llm_core() -> LLMCore:
    """Get LLM instance (singleton)"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMCore()
    return _llm_instance

def generate(prompt: str, system_prompt: str = "", mode: str = "chat", evc_state: Dict = None) -> str:
    """Backward compatible function"""
    llm = get_llm_core()
    if not system_prompt:
        system_prompt = "You are a helpful assistant. Respond in Thai language."
    return llm.generate(prompt, system_prompt, mode, evc_state)