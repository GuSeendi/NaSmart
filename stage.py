from datetime import date, datetime

STAGES = [
    {
        "name": "เตรียมดินและหว่านเมล็ด",
        "days": (0, 14),
        "risks": {
            "weather": "สูง — ความชื้นและอุณหภูมิกระทบอัตราการงอก",
            "pest":    "ต่ำ — แมลงยังไม่ระบาด",
            "disease": "ต่ำ — โรคยังไม่เกิด"
        },
        "advice": "เช็คความชื้นดินและพยากรณ์อากาศก่อนหว่านเมล็ด"
    },
    {
        "name": "งอกและเจริญเติบโต",
        "days": (15, 45),
        "risks": {
            "weather": "กลาง — ฝนหนักหรือแล้งชะลอการเจริญเติบโต",
            "pest":    "กลาง — ต้นอ่อนเสี่ยงถูกแมลงทำลาย",
            "disease": "กลาง — โรคเริ่มพัฒนาได้"
        },
        "advice": "เฝ้าระวังแมลงและโรคใบ ดูแลน้ำสม่ำเสมอ"
    },
    {
        "name": "สร้างผลผลิต",
        "days": (46, 90),
        "risks": {
            "weather": "สูง — อากาศแปรปรวนกระทบผลผลิตโดยตรง",
            "pest":    "สูง — แมลงคุกคามรวงข้าว",
            "disease": "สูง — โรคระบาดสร้างความเสียหายสูง"
        },
        "advice": "ระวังสูงสุด ตรวจแปลงทุกวัน ดูราคาข้าวตลาด"
    },
    {
        "name": "สุกแก่และเก็บเกี่ยว",
        "days": (91, 120),
        "risks": {
            "weather": "สูง — ฝนกระทบคุณภาพและปริมาณผลผลิต",
            "pest":    "ต่ำ — ความเสี่ยงลดลง",
            "disease": "ต่ำ — ความเสี่ยงลดลง"
        },
        "advice": "ติดตามพยากรณ์ฝนก่อนเก็บเกี่ยว เลือกช่วงอากาศดี"
    }
]

def get_days_since_planting(planting_date_str):
    planting = datetime.strptime(planting_date_str, "%Y-%m-%d").date()
    today = date.today()
    return (today - planting).days

def get_stage(planting_date_str):
    days = get_days_since_planting(planting_date_str)
    
    for stage in STAGES:
        start, end = stage["days"]
        if start <= days <= end:
            return {
                "days": days,
                "stage": stage
            }
    
    if days < 0:
        return {"days": days, "stage": None, "msg": f"ยังไม่ถึงวันหว่านเมล็ด\nเหลืออีก {abs(days)} วัน"}
    
    return {
        "days": days, 
        "stage": None, 
        "msg": (
            f"ผ่านมาแล้ว {days} วัน (เกินระยะ 120 วัน)\n"
            "ข้าวน่าจะเก็บเกี่ยวแล้ว\n"
            "---\n"
            "หากเริ่มรอบใหม่ กดปุ่ม ลงทะเบียน\n"
            "เพื่ออัปเดตวันหว่านเมล็ดใหม่"
        )
    }

def format_stage_message(planting_date_str):
    result = get_stage(planting_date_str)
    
    if result["stage"] is None:
        return result["msg"]
    
    days = result["days"]
    stage = result["stage"]
    start, end = stage["days"]
    days_left = end - days
    risks = stage["risks"]
    
    return (
        f"วันที่ปลูกมาแล้ว: {days} วัน\n"
        f"ระยะ: {stage['name']}\n"
        f"เหลืออีก {days_left} วันจะเข้าระยะถัดไป\n"
        f"---\n"
        f"ความเสี่ยงอากาศ: {risks['weather']}\n"
        f"ความเสี่ยงแมลง: {risks['pest']}\n"
        f"ความเสี่ยงโรค: {risks['disease']}\n"
        f"---\n"
        f"คำแนะนำ: {stage['advice']}"
    )
