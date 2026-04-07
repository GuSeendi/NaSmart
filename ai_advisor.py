import os
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def get_ai_advice(stage_info, weather_info, rice_price_info, farmer_question=""):
    prompt = f"""คุณคือ NaSmart ผู้ช่วย AI สำหรับชาวนาไทย 
ตอบเป็นภาษาไทยที่เข้าใจง่าย กระชับ ไม่เกิน 5 ประโยค

ข้อมูลปัจจุบันของแปลงนา:
{stage_info}

สภาพอากาศ:
{weather_info}

ราคาข้าว:
{rice_price_info}

{"คำถามชาวนา: " + farmer_question if farmer_question else "สรุปคำแนะนำที่สำคัญที่สุดสำหรับวันนี้"}

กรุณาวิเคราะห์และให้คำแนะนำที่เป็นประโยชน์ที่สุดสำหรับชาวนา"""

    models = ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
    
    for model in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={GEMINI_API_KEY}"
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 500}
            }
            
            res = requests.post(url, json=payload, timeout=30)
            data = res.json()
            
            if res.status_code == 200 and "candidates" in data:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            
            if res.status_code in (429, 404):
                continue
                
            return f"AI ไม่สามารถตอบได้ (Error {res.status_code})"
            
        except Exception as e:
            continue
    
    return (
        "ขณะนี้ AI มีผู้ใช้งานเยอะ\n"
        "กรุณาลองใหม่ใน 1-2 นาที\n"
        "หรือพิมพ์ ตรวจสอบ เพื่อดูข้อมูลระยะปลูก"
    )
