#!/usr/bin/env python3
"""
Setup และทดสอบ Ollama สำหรับ EVC Hybrid Chat
"""

import os
import sys
import requests
import subprocess
import time

def check_ollama_running():
    """ตรวจสอบว่า Ollama กำลังรันอยู่หรือไม่"""
    try:
        response = requests.get('http://localhost:11434', timeout=2)
        return response.status_code == 200
    except:
        return False

def start_ollama():
    """พยายามเริ่ม Ollama"""
    print("🚀 กำลังเริ่ม Ollama...")
    try:
        if sys.platform == "win32":
            subprocess.Popen(["ollama", "serve"], 
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(["ollama", "serve"], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
        time.sleep(3)
        return check_ollama_running()
    except FileNotFoundError:
        print("❌ ไม่พบคำสั่ง 'ollama' กรุณาติดตั้งจาก https://ollama.ai/download")
        return False
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        return False

def list_models():
    """แสดงรายการ models ที่ติดตั้งแล้ว"""
    try:
        result = subprocess.run(["ollama", "list"], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        return result.stdout
    except:
        return None

def pull_model(model_name):
    """ดาวน์โหลด model"""
    print(f"\n📥 กำลังดาวน์โหลด {model_name}...")
    print("⏳ อาจใช้เวลาสักครู่ (ขึ้นอยู่กับขนาดโมเดลและความเร็วเน็ต)")
    try:
        subprocess.run(["ollama", "pull", model_name], check=True)
        print(f"✅ ดาวน์โหลด {model_name} สำเร็จ!")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ ดาวน์โหลด {model_name} ล้มเหลว")
        return False
    except FileNotFoundError:
        print("❌ ไม่พบคำสั่ง 'ollama'")
        return False

def test_model(model_name):
    """ทดสอบ model"""
    print(f"\n🧪 ทดสอบ {model_name}...")
    try:
        response = requests.post(
            'http://localhost:11434/api/chat',
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant. Respond in Thai."},
                    {"role": "user", "content": "สวัสดีครับ แนะนำตัวหน่อย"}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 100
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            message = data.get("message", {}).get("content", "")
            print(f"✅ ทดสอบสำเร็จ!\n")
            print(f"📝 คำตอบจาก {model_name}:")
            print("-" * 60)
            print(message)
            print("-" * 60)
            return True
        else:
            print(f"❌ ทดสอบล้มเหลว (Status: {response.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        return False

def create_env_file(model_name):
    """สร้างไฟล์ .env"""
    env_content = f"""# EVC Hybrid Chat Configuration
LLM_PROVIDER=ollama
OPENAI_BASE_URL=http://localhost:11434
OPENAI_MODEL={model_name}
DEBUG_LOG=true
"""
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print(f"\n✅ สร้างไฟล์ .env เรียบร้อย (model: {model_name})")

def main():
    print("=" * 60)
    print("🤖 EVC Hybrid Chat - Ollama Setup Wizard")
    print("=" * 60)
    
    # ตรวจสอบ Ollama
    print("\n📡 กำลังตรวจสอบ Ollama...")
    if not check_ollama_running():
        print("⚠️  Ollama ไม่ได้รันอยู่")
        if not start_ollama():
            print("\n❌ ไม่สามารถเริ่ม Ollama ได้")
            print("\n📖 วิธีแก้ไข:")
            print("1. ติดตั้ง Ollama จาก: https://ollama.ai/download")
            print("2. เปิด Terminal/CMD ใหม่และรัน: ollama serve")
            print("3. รันสคริปต์นี้อีกครั้ง")
            return
    
    print("✅ Ollama กำลังรันอยู่")
    
    # แสดงรายการ models
    print("\n📋 Models ที่ติดตั้งแล้ว:")
    models_output = list_models()
    if models_output:
        print(models_output)
    else:
        print("  (ยังไม่มี models)")
    
    # แนะนำ models สำหรับภาษาไทย
    print("\n💡 Models ที่แนะนำสำหรับภาษาไทย:")
    recommended = [
        ("llama3:8b", "ดีที่สุด, ต้องใช้ RAM 8GB+", "~4.7GB"),
        ("qwen2:7b", "ดีสำหรับภาษาไทย", "~4.4GB"),
        ("llama2:7b", "รองลงมา, เสถียร", "~3.8GB"),
        ("phi3:mini", "เล็ก, เร็ว (ภาษาไทยพอใช้)", "~2.3GB")
    ]
    
    for i, (model, desc, size) in enumerate(recommended, 1):
        print(f"  {i}. {model:15} - {desc:30} [{size}]")
    
    # เลือก model
    print("\n❓ คุณต้องการติดตั้ง model ไหน?")
    choice = input("   เลือก (1-4) หรือพิมพ์ชื่อ model เอง [1]: ").strip()
    
    if not choice:
        choice = "1"
    
    if choice.isdigit() and 1 <= int(choice) <= 4:
        model_name = recommended[int(choice) - 1][0]
    else:
        model_name = choice
    
    # ตรวจสอบว่ามี model แล้วหรือไม่
    if models_output and model_name in models_output:
        print(f"\n✅ มี {model_name} อยู่แล้ว")
        skip = input("   ข้ามการดาวน์โหลด? (y/n) [y]: ").strip().lower()
        if skip != 'n':
            print("⏭️  ข้ามการดาวน์โหลด")
        else:
            pull_model(model_name)
    else:
        if not pull_model(model_name):
            return
    
    # ทดสอบ model
    print("\n" + "=" * 60)
    if not test_model(model_name):
        print("\n⚠️  การทดสอบล้มเหลว แต่ยังสามารถใช้งานได้")
    
    # สร้าง .env
    print("\n" + "=" * 60)
    create = input("สร้างไฟล์ .env อัตโนมัติ? (y/n) [y]: ").strip().lower()
    if create != 'n':
        create_env_file(model_name)
    
    # สรุป
    print("\n" + "=" * 60)
    print("✅ การตั้งค่าเสร็จสิ้น!")
    print("=" * 60)
    print("\n🚀 ขั้นตอนถัดไป:")
    print("1. ตรวจสอบไฟล์ .env")
    print("2. รัน: streamlit run app.py")
    print("3. เริ่มใช้งาน EVC Hybrid Chat!")
    print("\n💡 Tips:")
    print("- ถ้าตอบช้า ลองเปลี่ยนเป็น model เล็กกว่า")
    print("- ถ้าตอบไม่ดี ลองเปลี่ยนเป็น model ใหญ่กว่า")
    print("- ถ้าหมดแรม ปิดโปรแกรมอื่นก่อน")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  ยกเลิกการติดตั้ง")
    except Exception as e:
        print(f"\n❌ เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}")
        import traceback
        traceback.print_exc()