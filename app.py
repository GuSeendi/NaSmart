import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi,
    ReplyMessageRequest, TextMessage,
    QuickReply, QuickReplyItem, MessageAction
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from dotenv import load_dotenv
from database import Session, Farmer
from stage import format_stage_message
from weather import format_weather
from rice_price import get_rice_price, get_local_rice_price
from ai_advisor import get_ai_advice

load_dotenv()

app = Flask(__name__)
config = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# พิกัดกลางจังหวัด (lat, lon)
PROVINCE_COORDS = {
    "กรุงเทพ": (13.75, 100.50), "เชียงใหม่": (18.79, 98.98), "เชียงราย": (19.91, 99.83),
    "น่าน": (18.78, 100.77), "พะเยา": (19.17, 99.90), "แม่ฮ่องสอน": (19.30, 97.97),
    "แพร่": (18.14, 100.14), "ลำปาง": (18.29, 99.49), "ลำพูน": (18.57, 99.00),
    "อุตรดิตถ์": (17.62, 100.10), "พิษณุโลก": (16.82, 100.26), "สุโขทัย": (17.01, 99.82),
    "เพชรบูรณ์": (16.42, 101.16), "พิจิตร": (16.44, 100.35), "กำแพงเพชร": (16.48, 99.52),
    "นครสวรรค์": (15.69, 100.12), "ลพบุรี": (14.80, 100.62), "ชัยนาท": (15.19, 100.12),
    "อุทัยธานี": (15.38, 99.90), "สิงห์บุรี": (14.89, 100.40), "อ่างทอง": (14.59, 100.46),
    "สระบุรี": (14.53, 100.91), "อยุธยา": (14.35, 100.57), "สุพรรณบุรี": (14.47, 100.12),
    "นครนายก": (14.21, 101.21), "ปทุมธานี": (14.02, 100.53), "นนทบุรี": (13.86, 100.51),
    "นครปฐม": (13.82, 100.06), "สมุทรปราการ": (13.60, 100.60), "สมุทรสาคร": (13.55, 100.27),
    "สมุทรสงคราม": (13.41, 100.00),
    "หนองคาย": (17.88, 102.74), "นครพนม": (17.39, 104.78), "สกลนคร": (17.15, 104.15),
    "อุดรธานี": (17.42, 102.79), "หนองบัวลำภู": (17.20, 102.44), "เลย": (17.49, 101.72),
    "มุกดาหาร": (16.54, 104.72), "กาฬสินธุ์": (16.43, 103.51), "ขอนแก่น": (16.44, 102.83),
    "อำนาจเจริญ": (15.87, 104.63), "ยโสธร": (15.79, 104.15), "ร้อยเอ็ด": (16.05, 103.65),
    "มหาสารคาม": (16.18, 103.30), "ชัยภูมิ": (15.81, 102.03), "นครราชสีมา": (14.97, 102.10),
    "บุรีรัมย์": (14.99, 103.10), "สุรินทร์": (14.88, 103.49), "ศรีสะเกษ": (15.12, 104.33),
    "อุบลราชธานี": (15.23, 104.86),
    "สระแก้ว": (13.82, 102.07), "ปราจีนบุรี": (14.05, 101.37), "ฉะเชิงเทรา": (13.69, 101.07),
    "ชลบุรี": (13.36, 100.98), "ระยอง": (12.68, 101.28), "จันทบุรี": (12.61, 102.10), "ตราด": (12.24, 102.52),
    "ตาก": (16.88, 99.13), "กาญจนบุรี": (14.02, 99.53), "ราชบุรี": (13.54, 99.81),
    "เพชรบุรี": (13.11, 99.94), "ประจวบคีรีขันธ์": (11.81, 99.80),
    "ชุมพร": (10.49, 99.18), "ระนอง": (9.97, 98.63), "สุราษฎร์ธานี": (9.14, 99.33),
    "นครศรีธรรมราช": (8.43, 99.96), "กระบี่": (8.09, 98.91), "พังงา": (8.45, 98.53),
    "ภูเก็ต": (7.88, 98.39), "พัทลุง": (7.62, 100.08), "ตรัง": (7.56, 99.61),
    "ปัตตานี": (6.87, 101.25), "สงขลา": (7.19, 100.59), "สตูล": (6.62, 100.07),
    "นราธิวาส": (6.43, 101.82), "ยะลา": (6.54, 101.28),
}

def get_farmer_coords(farmer):
    """ดึงพิกัดจาก lat/lon หรือ fallback จากจังหวัด"""
    if farmer.latitude:
        return farmer.latitude, farmer.longitude
    if farmer.province and farmer.province in PROVINCE_COORDS:
        return PROVINCE_COORDS[farmer.province]
    return None, None

def reply(event, text):
    with ApiClient(config) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=text)]
            )
        )

def reply_with_quickreply(event, text, items):
    with ApiClient(config) as api_client:
        quick_reply_items = [
            QuickReplyItem(action=MessageAction(label=label, text=text_action))
            for label, text_action in items
        ]
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(
                    text=text,
                    quick_reply=QuickReply(items=quick_reply_items)
                )]
            )
        )

@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    except Exception:
        pass
    return "OK", 200

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    msg = event.message.text.strip()

    print(f"DEBUG msg: '{msg}'")

    session = Session()
    try:
        farmer = session.get(Farmer, user_id)

        if msg == "ลงทะเบียน":
            reply_with_quickreply(event,
                "ยินดีต้อนรับสู่ NaSmart!\nเลือกปีที่หว่านเมล็ด:",
                [
                    ("2568", "ปีหว่าน 2025"),
                    ("2569", "ปีหว่าน 2026"),
                ]
            )

        elif msg.startswith("ปีหว่าน "):
            year = msg.replace("ปีหว่าน ", "")
            months = [
                ("ม.ค.", f"เดือนหว่าน {year}-01"),
                ("ก.พ.", f"เดือนหว่าน {year}-02"),
                ("มี.ค.", f"เดือนหว่าน {year}-03"),
                ("เม.ย.", f"เดือนหว่าน {year}-04"),
                ("พ.ค.", f"เดือนหว่าน {year}-05"),
                ("มิ.ย.", f"เดือนหว่าน {year}-06"),
                ("ก.ค.", f"เดือนหว่าน {year}-07"),
                ("ส.ค.", f"เดือนหว่าน {year}-08"),
                ("ก.ย.", f"เดือนหว่าน {year}-09"),
                ("ต.ค.", f"เดือนหว่าน {year}-10"),
                ("พ.ย.", f"เดือนหว่าน {year}-11"),
                ("ธ.ค.", f"เดือนหว่าน {year}-12"),
            ]
            reply_with_quickreply(event, "เลือกเดือนที่หว่านเมล็ด:", months)

        elif msg.startswith("เดือนหว่าน "):
            ym = msg.replace("เดือนหว่าน ", "")  # e.g. 2026-03
            reply_with_quickreply(event,
                "เลือกช่วงวันที่หว่าน:",
                [
                    ("1-10",  f"ช่วงวัน {ym} 01"),
                    ("11-20", f"ช่วงวัน {ym} 11"),
                    ("21-31", f"ช่วงวัน {ym} 21"),
                ]
            )

        elif msg.startswith("ช่วงวัน "):
            parts = msg.replace("ช่วงวัน ", "").split(" ")  # e.g. ["2026-03", "01"]
            ym = parts[0]
            start = int(parts[1])
            days = []
            for d in range(start, start + 11):
                if d > 31:
                    break
                ds = f"{d:02d}"
                days.append((f"{d}", f"วันที่ {ym}-{ds}"))
            reply_with_quickreply(event, "เลือกวันที่หว่านเมล็ด:", days)

        elif msg == "เลือกพื้นที่":
            reply_with_quickreply(event,
                "เลือกภูมิภาคของคุณ:",
                [
                    ("ภาคเหนือ",   "ภาค ภาคเหนือ"),
                    ("ภาคกลาง ①",  "ภาค ภาคกลาง1"),
                    ("ภาคกลาง ②",  "ภาค ภาคกลาง2"),
                    ("ภาคอีสาน ①", "ภาค ภาคอีสาน1"),
                    ("ภาคอีสาน ②", "ภาค ภาคอีสาน2"),
                    ("ภาคตะวันออก", "ภาค ภาคตะวันออก"),
                    ("ภาคตะวันตก", "ภาค ภาคตะวันตก"),
                    ("ภาคใต้ ①",   "ภาค ภาคใต้1"),
                    ("ภาคใต้ ②",   "ภาค ภาคใต้2"),
                ]
            )

        elif msg == "เลือกชนิดข้าว":
            reply_with_quickreply(event,
                "เลือกชนิดข้าวที่ปลูก:",
                [
                    ("ข้าวหอมมะลิ", "ข้าว ข้าวหอมมะลิ"),
                    ("ข้าวเจ้า",    "ข้าว ข้าวเจ้า"),
                    ("ข้าวเหนียว",  "ข้าว ข้าวเหนียว"),
                    ("ข้าวหอมปทุม", "ข้าว ข้าวหอมปทุม"),
                    ("กข 79",       "ข้าว กข79"),
                ]
            )

        elif msg == "ตรวจสอบ":
            if farmer and farmer.planting_date:
                reply(event, format_stage_message(farmer.planting_date))
            else:
                reply(event, "กรุณาลงทะเบียนก่อนนะ\nพิมพ์: ลงทะเบียน")

        elif msg == "ราคาข้าว":
            reply(event, get_rice_price())

        elif msg.startswith("ราคาข้าว "):
            province = msg.replace("ราคาข้าว ", "")
            reply(event, get_local_rice_price(province))

        elif msg == "อากาศ":
            if farmer:
                lat, lon = get_farmer_coords(farmer)
                if lat:
                    reply(event, format_weather(lat, lon))
                else:
                    reply(event, "กรุณาเลือกพื้นที่หรือส่งพิกัดก่อนนะ")
            else:
                reply(event, "กรุณาลงทะเบียนก่อนนะ\nพิมพ์: ลงทะเบียน")

        elif msg == "สรุป":
            if farmer and farmer.planting_date:
                stage_info   = format_stage_message(farmer.planting_date)
                weather_info = "ไม่มีข้อมูลพิกัด"
                lat, lon = get_farmer_coords(farmer)
                if lat:
                    weather_info = format_weather(lat, lon)
                price_info   = get_rice_price()
                reply(event, f"{stage_info}\n\n{weather_info}\n\n{price_info}")
            else:
                reply(event, "กรุณาลงทะเบียนก่อนนะ\nพิมพ์: ลงทะเบียน")

        elif msg in ("แนะนำ", "ขอคำแนะนำ") or msg.startswith("ถาม "):
            if farmer and farmer.planting_date:
                stage_info   = format_stage_message(farmer.planting_date)
                weather_info = "ไม่มีข้อมูลพิกัด"
                lat, lon = get_farmer_coords(farmer)
                if lat:
                    weather_info = format_weather(lat, lon)
                price_info   = get_rice_price()
                question = msg.replace("ถาม ", "") if msg.startswith("ถาม ") else ""
                advice = get_ai_advice(stage_info, weather_info, price_info, question)
                reply(event, f"NaSmart AI แนะนำ:\n{advice}")
            else:
                reply(event, "กรุณาลงทะเบียนก่อนนะ\nพิมพ์: ลงทะเบียน")

        elif msg.startswith("วันที่ "):
            date_str = msg.replace("วันที่ ", "")
            if farmer:
                farmer.planting_date = date_str
            else:
                farmer = Farmer(user_id=user_id, planting_date=date_str)
                session.add(farmer)
            session.commit()
            reply(event,
                f"บันทึกวันหว่าน {date_str} แล้ว\n"
                "กดปุ่ม เลือกพื้นที่ เพื่อเลือกจังหวัด\n"
                "หรือส่งพิกัด: พิกัด LAT,LON"
            )

        elif msg.startswith("พิกัด "):
            try:
                coords = msg.replace("พิกัด ", "").split(",")
                lat, lng = float(coords[0]), float(coords[1])
                if farmer:
                    farmer.latitude  = lat
                    farmer.longitude = lng
                    session.commit()
                    reply(event, f"บันทึกพิกัดแล้ว\nลงทะเบียนเสร็จสมบูรณ์!")
                else:
                    reply(event, "กรุณาส่งวันที่หว่านก่อนนะ")
            except:
                reply(event, "รูปแบบพิกัดไม่ถูกต้อง\nเช่น: พิกัด 14.0000,100.0000")

        elif msg.startswith("ภาค "):
            region = msg.replace("ภาค ", "")
            provinces = {
                "ภาคเหนือ": [
                    ("เชียงราย","จังหวัด เชียงราย"),("น่าน","จังหวัด น่าน"),("พะเยา","จังหวัด พะเยา"),
                    ("เชียงใหม่","จังหวัด เชียงใหม่"),("แม่ฮ่องสอน","จังหวัด แม่ฮ่องสอน"),("แพร่","จังหวัด แพร่"),
                    ("ลำปาง","จังหวัด ลำปาง"),("ลำพูน","จังหวัด ลำพูน"),("อุตรดิตถ์","จังหวัด อุตรดิตถ์"),
                ],
                "ภาคกลาง1": [
                    ("กรุงเทพ","จังหวัด กรุงเทพ"),("พิษณุโลก","จังหวัด พิษณุโลก"),("สุโขทัย","จังหวัด สุโขทัย"),
                    ("เพชรบูรณ์","จังหวัด เพชรบูรณ์"),("พิจิตร","จังหวัด พิจิตร"),("กำแพงเพชร","จังหวัด กำแพงเพชร"),
                    ("นครสวรรค์","จังหวัด นครสวรรค์"),("ลพบุรี","จังหวัด ลพบุรี"),("ชัยนาท","จังหวัด ชัยนาท"),
                    ("อุทัยธานี","จังหวัด อุทัยธานี"),("สิงห์บุรี","จังหวัด สิงห์บุรี"),
                ],
                "ภาคกลาง2": [
                    ("อ่างทอง","จังหวัด อ่างทอง"),("สระบุรี","จังหวัด สระบุรี"),("อยุธยา","จังหวัด อยุธยา"),
                    ("สุพรรณบุรี","จังหวัด สุพรรณบุรี"),("นครนายก","จังหวัด นครนายก"),("ปทุมธานี","จังหวัด ปทุมธานี"),
                    ("นนทบุรี","จังหวัด นนทบุรี"),("นครปฐม","จังหวัด นครปฐม"),("สมุทรปราการ","จังหวัด สมุทรปราการ"),
                    ("สมุทรสาคร","จังหวัด สมุทรสาคร"),("สมุทรสงคราม","จังหวัด สมุทรสงคราม"),
                ],
                "ภาคอีสาน1": [
                    ("หนองคาย","จังหวัด หนองคาย"),("นครพนม","จังหวัด นครพนม"),("สกลนคร","จังหวัด สกลนคร"),
                    ("อุดรธานี","จังหวัด อุดรธานี"),("หนองบัวลำภู","จังหวัด หนองบัวลำภู"),("เลย","จังหวัด เลย"),
                    ("มุกดาหาร","จังหวัด มุกดาหาร"),("กาฬสินธุ์","จังหวัด กาฬสินธุ์"),("ขอนแก่น","จังหวัด ขอนแก่น"),
                    ("อำนาจเจริญ","จังหวัด อำนาจเจริญ"),
                ],
                "ภาคอีสาน2": [
                    ("ยโสธร","จังหวัด ยโสธร"),("ร้อยเอ็ด","จังหวัด ร้อยเอ็ด"),("มหาสารคาม","จังหวัด มหาสารคาม"),
                    ("ชัยภูมิ","จังหวัด ชัยภูมิ"),("นครราชสีมา","จังหวัด นครราชสีมา"),("บุรีรัมย์","จังหวัด บุรีรัมย์"),
                    ("สุรินทร์","จังหวัด สุรินทร์"),("ศรีสะเกษ","จังหวัด ศรีสะเกษ"),("อุบลราชธานี","จังหวัด อุบลราชธานี"),
                ],
                "ภาคตะวันออก": [
                    ("สระแก้ว","จังหวัด สระแก้ว"),("ปราจีนบุรี","จังหวัด ปราจีนบุรี"),("ฉะเชิงเทรา","จังหวัด ฉะเชิงเทรา"),
                    ("ชลบุรี","จังหวัด ชลบุรี"),("ระยอง","จังหวัด ระยอง"),("จันทบุรี","จังหวัด จันทบุรี"),("ตราด","จังหวัด ตราด"),
                ],
                "ภาคตะวันตก": [
                    ("ตาก","จังหวัด ตาก"),("กาญจนบุรี","จังหวัด กาญจนบุรี"),("ราชบุรี","จังหวัด ราชบุรี"),
                    ("เพชรบุรี","จังหวัด เพชรบุรี"),("ประจวบฯ","จังหวัด ประจวบคีรีขันธ์"),
                ],
                "ภาคใต้1": [
                    ("ชุมพร","จังหวัด ชุมพร"),("ระนอง","จังหวัด ระนอง"),("สุราษฎร์ธานี","จังหวัด สุราษฎร์ธานี"),
                    ("นครศรีฯ","จังหวัด นครศรีธรรมราช"),("กระบี่","จังหวัด กระบี่"),("พังงา","จังหวัด พังงา"),("ภูเก็ต","จังหวัด ภูเก็ต"),
                ],
                "ภาคใต้2": [
                    ("พัทลุง","จังหวัด พัทลุง"),("ตรัง","จังหวัด ตรัง"),("ปัตตานี","จังหวัด ปัตตานี"),
                    ("สงขลา","จังหวัด สงขลา"),("สตูล","จังหวัด สตูล"),("นราธิวาส","จังหวัด นราธิวาส"),("ยะลา","จังหวัด ยะลา"),
                ],
            }
            if region in provinces:
                label = region.replace("1"," ①").replace("2"," ②")
                reply_with_quickreply(event, f"เลือกจังหวัด ({label}):", provinces[region])

        elif msg.startswith("จังหวัด "):
            province = msg.replace("จังหวัด ", "")
            if farmer:
                farmer.province = province
                session.commit()
                reply(event, f"บันทึกจังหวัด {province} แล้ว")
            else:
                reply(event, "กรุณาลงทะเบียนก่อนนะ\nพิมพ์: ลงทะเบียน")

        elif msg.startswith("ข้าว "):
            variety = msg.replace("ข้าว ", "")
            if farmer:
                farmer.rice_variety = variety
                session.commit()
                reply(event, f"บันทึกชนิดข้าว {variety} แล้ว")
            else:
                reply(event, "กรุณาลงทะเบียนก่อนนะ\nพิมพ์: ลงทะเบียน")

        elif msg == "แก้ไขข้อมูล":
            reply_with_quickreply(event,
                "แก้ไขข้อมูลได้เลย\nเลือกสิ่งที่ต้องการแก้ไข:",
                [
                    ("เปลี่ยนวันหว่าน", "ลงทะเบียน"),
                    ("เปลี่ยนพื้นที่", "เลือกพื้นที่"),
                    ("เปลี่ยนชนิดข้าว", "เลือกชนิดข้าว"),
                    ("ยกเลิกทั้งหมด", "ยกเลิกการลงทะเบียน"),
                ]
            )

        elif msg == "ยกเลิกการลงทะเบียน":
            if farmer:
                session.delete(farmer)
                session.commit()
                reply(event,
                    "ลบข้อมูลของคุณเรียบร้อยแล้ว\n"
                    "พิมพ์ ลงทะเบียน เพื่อเริ่มใหม่ได้เลย"
                )
            else:
                reply(event, "ยังไม่มีข้อมูลของคุณในระบบ")

        elif msg == "ข้อมูลของฉัน":
            if farmer:
                reply(event,
                    f"ข้อมูลของคุณ\n"
                    f"---\n"
                    f"วันหว่านเมล็ด: {farmer.planting_date or 'ยังไม่มี'}\n"
                    f"จังหวัด: {farmer.province or 'ยังไม่มี'}\n"
                    f"ชนิดข้าว: {farmer.rice_variety or 'ยังไม่มี'}\n"
                    f"ละติจูด: {farmer.latitude or 'ยังไม่มี'}\n"
                    f"ลองจิจูด: {farmer.longitude or 'ยังไม่มี'}"
                )
            else:
                reply(event, "ยังไม่มีข้อมูลของคุณ\nพิมพ์: ลงทะเบียน")

        else:
            reply(event,
                "NaSmart คำสั่งที่ใช้ได้\n"
                "---\n"
                "ลงทะเบียน — เริ่มต้นใช้งาน\n"
                "ข้อมูลของฉัน — ดูข้อมูลที่บันทึก\n"
                "แก้ไขข้อมูล — เปลี่ยนวันที่หรือพิกัด\n"
                "ยกเลิกการลงทะเบียน — ลบข้อมูล\n"
                "---\n"
                "ตรวจสอบ — ดูระยะปลูกและความเสี่ยง\n"
                "อากาศ — พยากรณ์อากาศแปลงนา\n"
                "ราคาข้าว — ราคาข้าววันนี้\n"
                "แนะนำ — AI วิเคราะห์และแนะนำ"
            )

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        reply(event, "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง")

    finally:
        session.close()

if __name__ == "__main__":
    app.run(port=5000)