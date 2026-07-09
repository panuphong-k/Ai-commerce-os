# app.py
import os
import uuid
import streamlit as st
from google import genai
from google.genai import types

from prompts import SYSTEM_PROMPT, build_user_prompt
from video_creator import create_video, text_to_speech

GEMINI_MODEL_NAME = "gemini-2.5-flash"
st.set_page_config(page_title="Ai-commerce-os", page_icon="🤖", layout="centered")

st.title("🤖 Ai-commerce-os")
st.subheader("ระบบสร้างคลิปวิดีโอและเสียงพากย์ส่งต่อ CapCut อัตโนมัติ")
st.write("ระบบจะเจนเนอเรตวิดีโอและเสียงพากย์ที่พร้อมใช้งานกับ CapCut ได้ฟรี 100%")

product_name = st.text_input("📦 ชื่อสินค้า", placeholder="เช่น ครีมกันแดดสูตรคุมมัน")
pain_point = st.text_area("🔥 ปัญหาของลูกค้าก่อนใช้สินค้า", placeholder="เช่น หน้าเยิ้มระหว่างวัน เมคอัพหลุด ทาแล้ววอกลอย")

api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.warning("⚠️ ไม่พบ GEMINI_API_KEY โปรดใส่ API Key ใน Environment หรือ Secrets ก่อนใช้งาน")

if st.button("🚀 เริ่มสร้างสื่อคลิป AI", type="primary", disabled=not api_key):
    if not product_name or not pain_point:
        st.error("❌ โปรดกรอกข้อมูลให้ครบทั้งชื่อสินค้าและปัญหาของลูกค้า")
    else:
        os.makedirs("output", exist_ok=True)
        unique_id = uuid.uuid4().hex
        audio_output_path = f"output/audio_{unique_id}.mp3"
        video_output_path = f"output/final_video_{unique_id}.mp4"
        
        # สร้างตัวแปรเก็บบทพากย์ไว้ใช้นอกบล็อกเสร็จสิ้น
        script_text = ""
        
        try:
            with st.status("🎬 กำลังประมวลผลระบบ Ai-commerce-os...", expanded=True) as status:
                status.update(label="🧠 1. กำลังวิเคราะห์มุมมองและคิดสคริปต์สไตล์ TikTok...")
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model=GEMINI_MODEL_NAME,
                    contents=build_user_prompt(product_name, pain_point),
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
                )
                script_text = response.text
                st.text_area("📝 บทพากย์เสียงที่ AI คิดให้ (ก๊อปปี้ไปวางใน CapCut ได้):", script_text, height=120)
                
                status.update(label="🔊 2. กำลังแปลงเสียงพากย์ภาษาไทยที่เป็นธรรมชาติ (Edge-TTS)...")
                text_to_speech(script_text, audio_output_path)
                
                status.update(label="🎥 3. กำลังสร้างวิดีโอเคลื่อนไหว Dynamic Gradient (MoviePy)...")
                create_video(audio_output_path, video_output_path)
                
                status.update(label="✨ ประมวลผลสื่อทั้งหมดสําเร็จ!", state="complete")
                
            st.success("🎉 คลิปวิดีโอและซาวด์เสียงของคุณพร้อมส่งต่อไปยัง CapCut แล้ว!")
            st.video(video_output_path)
            
            # ----------------------------------------------------------------------
            # 📦 โซนดาวน์โหลดไฟล์สำหรับนำไปแก้ไขใน CapCut
            # ----------------------------------------------------------------------
            st.write("### 📥 เลือกดาวน์โหลดไฟล์สำหรับนำไปจัดสร้างต่อใน CapCut:")
            
            col1, col2 = st.columns(2)
            
            with col1:
                with open(video_output_path, "rb") as file:
                    st.download_button(
                        label="🎬 ดาวน์โหลดวิดีโอรวมเสียง (.MP4)",
                        data=file,
                        file_name=f"capcut_video_{product_name}.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )
                st.caption("💡 นำเข้าคลิปนี้ใน CapCut แล้วใช้ฟังก์ชัน 'แยกเสียงออก (Extract Audio)' เพื่อตัดต่อเปลี่ยนภาพพื้นหลังได้อิสระ")

            with col2:
                with open(audio_output_path, "rb") as file:
                    st.download_button(
                        label="🔊 ดาวน์โหลดเฉพาะเสียงพากย์ (.MP3)",
                        data=file,
                        file_name=f"voice_{product_name}.mp3",
                        mime="audio/mp3",
                        use_container_width=True
                    )
                st.caption("💡 เหมาะสำหรับการนำไปวางบนฟุตเทจสำเร็จรูปของ CapCut หรือใช้ระบบ Auto Captions เจนคำบรรยาย")

        except Exception as e:
            st.error(f"🚫 เกิดข้อผิดพลาดระหว่างทำงาน: {e}")