"""
app.py
------
หน้าเว็บหลักของโปรเจกต์ "Ai-commerce-os"
สร้างด้วย Streamlit สำหรับให้ผู้ใช้กรอกชื่อสินค้าและปัญหาของลูกค้า
แล้วระบบจะ:
  1. เรียก Gemini (ผ่าน google-genai SDK) เพื่อคิดสคริปต์รีวิวสไตล์ TikTok
  2. แปลงสคริปต์เป็นเสียงพากย์ภาษาไทยด้วย edge-tts
  3. ประกอบเสียงเข้ากับวิดีโอพื้นหลัง (assets/background.mp4) ด้วย moviepy
  4. แสดงผลวิดีโอให้ดูตัวอย่าง พร้อมปุ่มดาวน์โหลด

วิธี Deploy บน Streamlit Community Cloud:
  - อัปโหลดโปรเจกต์นี้ขึ้น GitHub repo
  - ไปที่ share.streamlit.io แล้วเชื่อมกับ repo นี้ เลือกไฟล์หลักเป็น app.py
  - ไปที่ App settings -> Secrets แล้วเพิ่ม:
        GEMINI_API_KEY = "ใส่ API Key ของคุณตรงนี้"
  - อย่าลืมอัปโหลดไฟล์ assets/background.mp4 (วิดีโอพื้นหลัง) เข้าไปใน repo ด้วย
"""

import os
import uuid

import streamlit as st
from google import genai
from google.genai import types

from prompts import SYSTEM_PROMPT, build_user_prompt
from video_creator import create_video, text_to_speech

# -----------------------------------------------------------------------
# ค่าคงที่และการตั้งค่าหน้าเว็บ
# -----------------------------------------------------------------------
# หมายเหตุ: หากชื่อโมเดลนี้ถูก Google ปลดระวางในอนาคต
# สามารถเปลี่ยนเป็นรุ่นใหม่กว่าได้ที่บรรทัดเดียวนี้
GEMINI_MODEL_NAME = "gemini-2.5-flash"

st.set_page_config(
    page_title="Ai-commerce-os | สร้างคลิปรีวิวสินค้าอัตโนมัติ",
    page_icon="🛍️",
    layout="centered",
)


# -----------------------------------------------------------------------
# ฟังก์ชันช่วยเรียก Gemini เพื่อสร้างสคริปต์
# -----------------------------------------------------------------------
def generate_script(product_name: str, customer_problem: str) -> str:
    """
    เรียก Gemini ผ่าน google-genai SDK เพื่อสร้างบทพากย์เสียง TikTok

    Args:
        product_name: ชื่อสินค้า
        customer_problem: ปัญหาของลูกค้าก่อนใช้สินค้า

    Returns:
        บทพากย์เสียงที่ AI สร้างขึ้น (ข้อความล้วน)

    Raises:
        RuntimeError: หากไม่พบ API Key หรือเรียก API ไม่สำเร็จ
    """
    # ใช้ try/except ครอบการอ่าน st.secrets เพราะบางเวอร์ชันของ Streamlit
    # จะ raise Exception ทันทีหากยังไม่เคยตั้งค่าไฟล์ secrets.toml เลยสักครั้ง
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:  # noqa: BLE001 - ไม่ว่า secrets จะยังไม่ถูกตั้งค่าด้วยสาเหตุใด ให้ถือว่าไม่มี key
        api_key = None

    if not api_key:
        raise RuntimeError(
            "ไม่พบ GEMINI_API_KEY ใน st.secrets กรุณาตั้งค่า Secret "
            "ในหน้า App settings ของ Streamlit Community Cloud ก่อนใช้งาน"
        )

    # สร้าง Client ของ google-genai SDK (เวอร์ชันใหม่)
    client = genai.Client(api_key=api_key)

    user_prompt = build_user_prompt(product_name, customer_problem)

    response = client.models.generate_content(
        model=GEMINI_MODEL_NAME,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.9,  # เพิ่มความสร้างสรรค์ให้สคริปต์ไม่ซ้ำซากจำเจ
        ),
    )

    script_text = (response.text or "").strip()
    if not script_text:
        raise RuntimeError("Gemini ไม่ส่งข้อความสคริปต์กลับมา กรุณาลองใหม่อีกครั้ง")

    return script_text


# -----------------------------------------------------------------------
# ส่วนหัวของหน้าเว็บ
# -----------------------------------------------------------------------
st.title("🛍️ Ai-commerce-os")
st.caption("สร้างวิดีโอรีวิวสินค้าสไตล์ TikTok อัตโนมัติ ด้วย Gemini + edge-tts")

st.divider()

# -----------------------------------------------------------------------
# ฟอร์มรับข้อมูลจากผู้ใช้
# -----------------------------------------------------------------------
product_name = st.text_input(
    "ชื่อสินค้า",
    placeholder="เช่น เซรั่มลดสิวสูตรเข้มข้น",
)

customer_problem = st.text_area(
    "ปัญหาของลูกค้าก่อนใช้สินค้า",
    placeholder="เช่น หน้ามันเยิ้ม เป็นสิวอักเสบบ่อย ใช้ครีมมาหลายยี่ห้อแล้วไม่ดีขึ้น",
    height=100,
)

start_button = st.button("🎬 เริ่มสร้างคลิป AI", type="primary", use_container_width=True)

st.divider()

# -----------------------------------------------------------------------
# Logic หลัก: เมื่อกดปุ่ม "เริ่มสร้างคลิป AI"
# -----------------------------------------------------------------------
if start_button:
    # --- ตรวจสอบความครบถ้วนของข้อมูล input ก่อน ---
    if not product_name.strip() or not customer_problem.strip():
        st.warning("⚠️ กรุณากรอกทั้ง 'ชื่อสินค้า' และ 'ปัญหาของลูกค้า' ให้ครบก่อนเริ่มสร้างคลิป")
    else:
        # สร้างชื่อไฟล์ที่ไม่ซ้ำกันในแต่ละการรัน (unique ต่อ 1 คลิก)
        # ป้องกันปัญหาไฟล์ชนกัน (race condition) เมื่อมีผู้ใช้หลายคนกดปุ่มพร้อมกัน
        # บน Streamlit Community Cloud ซึ่งอาจใช้ process เดียวกันรองรับหลาย session
        run_id = uuid.uuid4().hex
        audio_output_path = f"output_audio_{run_id}.mp3"
        video_output_path = f"final_video_{run_id}.mp4"

        # ใช้ st.status เพื่อแสดงความคืบหน้าแต่ละขั้นตอนให้ผู้ใช้เห็นชัดเจน
        with st.status("กำลังสร้างคลิปวิดีโอ...", expanded=True) as status:
            try:
                # ขั้นที่ 1: สร้างสคริปต์ด้วย Gemini
                st.write("✍️ กำลังคิดสคริปต์ด้วย Gemini...")
                script_text = generate_script(product_name, customer_problem)
                st.success("ได้สคริปต์เรียบร้อยแล้ว")
                st.text_area("📝 สคริปต์ที่ AI สร้างขึ้น", value=script_text, height=150)

                # ขั้นที่ 2: แปลงสคริปต์เป็นเสียงพากย์
                st.write("🔊 กำลังแปลงสคริปต์เป็นเสียงพากย์ภาษาไทย...")
                text_to_speech(script_text, output_path=audio_output_path)
                st.success("สร้างไฟล์เสียงพากย์เรียบร้อยแล้ว")

                # ขั้นที่ 3: ประกอบเสียงเข้ากับวิดีโอพื้นหลัง
                st.write("🎞️ กำลังประกอบวิดีโอ...")
                create_video(
                    audio_path=audio_output_path,
                    output_video_path=video_output_path,
                )
                st.success("สร้างวิดีโอเสร็จสมบูรณ์!")

                status.update(label="✅ สร้างคลิปสำเร็จ!", state="complete", expanded=False)

                # --- แสดงผลวิดีโอและปุ่มดาวน์โหลด ---
                st.subheader("🎉 วิดีโอของคุณพร้อมแล้ว")
                st.video(video_output_path)

                with open(video_output_path, "rb") as video_file:
                    st.download_button(
                        label="⬇️ ดาวน์โหลดวิดีโอ (.mp4) สำหรับลง TikTok",
                        data=video_file,
                        file_name="tiktok_review_video.mp4",
                        mime="video/mp4",
                        use_container_width=True,
                    )

            except FileNotFoundError as e:
                # --- Error Handling: กรณีหาไฟล์ assets/background.mp4 ไม่เจอ ---
                status.update(label="❌ ไม่พบวิดีโอพื้นหลัง", state="error", expanded=True)
                st.error(
                    "🚫 **ไม่พบไฟล์วิดีโอพื้นหลัง (assets/background.mp4)**\n\n"
                    "กรุณาอัปโหลดไฟล์วิดีโอพื้นหลังไว้ในโฟลเดอร์ `assets/` ของโปรเจกต์ "
                    "แล้วตั้งชื่อไฟล์ว่า `background.mp4` ก่อนกดสร้างคลิปอีกครั้ง"
                )
                st.caption(f"รายละเอียดข้อผิดพลาด: {e}")

            except RuntimeError as e:
                # --- Error Handling: กรณี API Key ผิด / Gemini เรียกไม่สำเร็จ / edge-tts ล้มเหลว ---
                status.update(label="❌ เกิดข้อผิดพลาด", state="error", expanded=True)
                st.error(f"🚫 เกิดข้อผิดพลาดระหว่างสร้างคลิป: {e}")

            except Exception as e:  # noqa: BLE001 - ดักข้อผิดพลาดอื่นๆ ที่ไม่คาดคิด ไม่ให้แอปล่ม
                status.update(label="❌ เกิดข้อผิดพลาดที่ไม่คาดคิด", state="error", expanded=True)
                st.error(f"🚫 เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}")

            finally:
                # ลบไฟล์เสียงชั่วคราวทิ้ง เพื่อไม่ให้ค้างอยู่บน server (วิดีโอเก็บไว้ให้ดาวน์โหลด)
                if os.path.exists(audio_output_path):
                    try:
                        os.remove(audio_output_path)
                    except OSError:
                        pass

st.divider()
st.caption(
    "💡 เคล็ดลับ: วางไฟล์วิดีโอพื้นหลัง (แนวตั้ง 9:16 แนะนำ) ไว้ที่ `assets/background.mp4` "
    "ก่อน Deploy ขึ้น Streamlit Community Cloud"
)
