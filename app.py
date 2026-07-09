# ปรับโค้ดในไฟล์ app.py ช่วงที่กดปุ่มสร้างคลิปให้เป็นรูปแบบนี้:
        try:
            with st.status("🎬 กำลังประมวลผลระบบ Ai-commerce-os...", expanded=True) as status:
                status.update(label="🧠 1. กำลังคิดบทสคริปต์แนววัยรุ่น TikTok ด้วย Gemini...")
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model=GEMINI_MODEL_NAME,
                    contents=build_user_prompt(product_name, pain_point),
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
                )
                script_text = response.text
                st.text_area("📝 บทพากย์เสียงวัยรุ่นที่ AI คิดให้:", script_text, height=120)
                
                status.update(label="🔊 2. กำลังแปลงเสียงพากย์ภาษาไทยวัยรุ่น (Edge-TTS)...")
                text_to_speech(script_text, audio_output_path)
                
                status.update(label="🎥 3. กำลังประกอบวิดีโอภาพการ์ตูนมินิมอลพาสเทล...")
                # สั่งรันสร้างวิดีโอภาพการ์ตูน (ส่งตัวแปรให้ครบตามเดิม)
                create_video(audio_output_path, "", video_output_path)
                
                status.update(label="✨ สร้างคลิปวิดีโอสำเร็จ!", state="complete")
                
            st.success("🎉 วิดีโอภาพการ์ตูน + เสียงพากย์วัยรุ่น พร้อมใช้งานแล้ว!")
            st.video(video_output_path)
            
            with open(video_output_path, "rb") as file:
                st.download_button(
                    label="📥 ดาวน์โหลดวิดีโอสำหรับนำไปใส่ CapCut / ลง TikTok",
                    data=file,
                    file_name=f"tiktok_cartoon_{product_name}.mp4",
                    mime="video/mp4"
                )
        except Exception as e:
            st.error(f"🚫 เกิดข้อผิดพลาดในระบบ: {e}")
        finally:
            if os.path.exists(audio_output_path):
                try: os.remove(audio_output_path)
                except: pass