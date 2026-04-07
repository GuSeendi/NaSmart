import os
import requests
from dotenv import load_dotenv

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

def get_weather(lat, lon):
    try:
        # อากาศปัจจุบัน
        url_now = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}&lon={lon}"
            f"&appid={WEATHER_API_KEY}"
            f"&units=metric&lang=th"
        )
        # พยากรณ์ 3 วัน
        url_forecast = (
            f"https://api.openweathermap.org/data/2.5/forecast"
            f"?lat={lat}&lon={lon}"
            f"&appid={WEATHER_API_KEY}"
            f"&units=metric&lang=th&cnt=3"
        )

        now      = requests.get(url_now, timeout=5).json()
        forecast = requests.get(url_forecast, timeout=5).json()

        weather  = now["weather"][0]["description"]
        temp     = now["main"]["temp"]
        humidity = now["main"]["humidity"]
        rain     = now.get("rain", {}).get("1h", 0)

        # พยากรณ์วันถัดไป
        forecast_lines = []
        seen_dates = []
        for item in forecast["list"]:
            date_str = item["dt_txt"][:10]
            if date_str not in seen_dates:
                seen_dates.append(date_str)
                desc  = item["weather"][0]["description"]
                tmax  = item["main"]["temp_max"]
                tmin  = item["main"]["temp_min"]
                forecast_lines.append(f"{date_str}: {desc} {tmin}-{tmax}°C")
            if len(seen_dates) >= 3:
                break

        forecast_text = "\n".join(forecast_lines)

        return (
            f"สภาพอากาศปัจจุบัน\n"
            f"สภาพฟ้า: {weather}\n"
            f"อุณหภูมิ: {temp} °C\n"
            f"ความชื้น: {humidity}%\n"
            f"ฝน (1 ชม.): {rain} มม.\n"
            f"---\n"
            f"พยากรณ์ 3 วัน\n"
            f"{forecast_text}"
        )
    except Exception as e:
        return f"ดึงข้อมูลอากาศไม่ได้: {str(e)}"

def format_weather(lat, lon):
    return get_weather(lat, lon)
