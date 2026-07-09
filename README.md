# 🛍️ Ai-commerce-os

เว็บแอปสร้างวิดีโอรีวิวสินค้าสไตล์ TikTok อัตโนมัติ จาก "ชื่อสินค้า" และ "ปัญหาของลูกค้า"
ใช้ Gemini (ผ่าน `google-genai` SDK) คิดสคริปต์ และ `edge-tts` พากย์เสียงภาษาไทย
ประกอบวิดีโอด้วย `moviepy` แล้วรันบน Streamlit

## โครงสร้างโปรเจกต์
```
Ai-commerce-os/
├── app.py                          # หน้าเว็บหลัก (Streamlit UI)
├── prompts.py                      # System/User Prompt สำหรับ Gemini
├── video_creator.py                # แปลงข้อความเป็นเสียง + ประกอบวิดีโอ
├── requirements.txt                # รายการ Library
├── assets/
│   └── background.mp4              # วิดีโอพื้นหลัง (ต้องเพิ่มเอง ดูด้านล่าง)
└── .streamlit/
    └── secrets.toml.example        # ตัวอย่างการตั้งค่า API Key
```

## ⚠️ สิ่งที่ต้องเตรียมก่อนใช้งาน
1. **วิดีโอพื้นหลัง**: นำไฟล์วิดีโอ (แนะนำแนวตั้ง 9:16, ไม่มีลิขสิทธิ์ติดปัญหา) มาวางไว้ที่
   `assets/background.mp4` — หากไม่มีไฟล์นี้ แอปจะแจ้งเตือนข้อผิดพลาดบนหน้าเว็บ
2. **Gemini API Key**: ขอฟรีได้ที่ [Google AI Studio](https://aistudio.google.com/apikey)

## 🖥️ รันบนเครื่อง Local
```bash
pip install -r requirements.txt

# ตั้งค่า API Key สำหรับทดสอบบนเครื่อง
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# แล้วแก้ไฟล์ .streamlit/secrets.toml ใส่ API Key จริง

streamlit run app.py
```

## ☁️ Deploy บน Streamlit Community Cloud (ฟรี)
1. Push โปรเจกต์นี้ขึ้น GitHub repository (อย่าลืม `assets/background.mp4` ด้วย)
2. เข้า [share.streamlit.io](https://share.streamlit.io) แล้วกด **New app**
3. เลือก repo นี้ และตั้งค่า Main file path เป็น `app.py`
4. ไปที่ **App settings -> Secrets** แล้ววางข้อความนี้ (แก้ค่า API Key ให้เป็นของจริง):
   ```
   GEMINI_API_KEY = "ใส่ Gemini API Key ของคุณตรงนี้"
   ```
5. กด Deploy รอสักครู่ แอปก็จะพร้อมใช้งานผ่านลิงก์สาธารณะ

## หมายเหตุเรื่องโมเดล
โค้ดตั้งค่าเริ่มต้นไว้ที่ `gemini-2.5-flash` ใน `app.py` (ตัวแปร `GEMINI_MODEL_NAME`)
หากต้องการเปลี่ยนเป็นรุ่นอื่น สามารถแก้ได้ที่บรรทัดเดียวในไฟล์นั้น
