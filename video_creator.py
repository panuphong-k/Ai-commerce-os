import asyncio
import os
import random
import edge_tts
from moviepy import AudioFileClip, ImageClip

# ใช้เสียงผู้หญิง th-TH-PremwadeeNeural ซึ่งเป็นเสียงที่ดูเป็นวัยรุ่นและธรรมชาติที่สุด
DEFAULT_VOICE = "th-TH-PremwadeeNeural"

async def _generate_speech_async(text: str, output_path: str, voice: str) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(output_path)

def text_to_speech(script_text: str, output_path: str, voice: str = DEFAULT_VOICE) -> None:
    try:
        asyncio.run(_generate_speech_async(script_text, output_path, voice))
    except Exception as exc:
        raise RuntimeError(f"เกิดข้อผิดพลาดในการแปลงเสียงพากย์: {exc}") from exc

def download_cartoon_background():
    """สุ่มลิงก์ภาพการ์ตูน/วอลเปเปอร์แนวตั้งสวยๆ สไตล์มินิมอล พาสเทล จาก Unsplash"""
    import requests
    
    # Keyword ค้นหาภาพการ์ตูน/พาสเทลน่ารักๆ ที่เหมาะกับทำพื้นหลัง TikTok
    keywords = ["cartoon-background", "pastel-illustration", "anime-wallpaper", "cute-pattern", "minimal-art"]
    selected_keyword = random.choice(keywords)
    
    # ดึงภาพแนวตั้งขนาด 1080x1920 (9:16)
    url = f"https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1080&h=1920&fit=crop" 
    
    # ตัวเลือกภาพการ์ตูน/อาร์ตพาสเทลแบบสุ่มอื่นๆ
    backup_urls = [
        "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe", # Abstract Pastel
        "https://images.unsplash.com/photo-1579546929518-9e396f3cc809", # Gradient Pop
        "https://images.unsplash.com/photo-1604871000636-074fa5117945", # Minimal Art
    ]
    random_url = random.choice(backup_urls) + "?auto=format&fit=crop&w=1080&h=1920"
    
    temp_bg_path = "temp_cartoon_bg.jpg"
    try:
        response = requests.get(random_url, timeout=10)
        if response.status_code == 200:
            with open(temp_bg_path, "wb") as f:
                f.write(response.content)
            return temp_bg_path
    except:
        pass
        
    # หากดาวน์โหลดไม่ได้ ให้สร้างภาพสีชมพูพาสเทลการ์ตูนๆ ขึ้นมาเองเป็นตัวสำรอง
    from PIL import Image
    img = Image.new("RGB", (1080, 1920), color=(255, 200, 220))
    img.save(temp_bg_path)
    return temp_bg_path

def create_video(audio_path: str, background_video_path: str, output_video_path: str) -> None:
    """สร้างวิดีโอจากภาพการ์ตูนพื้นหลังที่สุ่มมาอัตโนมัติ ยืดเวลาตามเสียงพากย์วัยรุ่น"""
    audio_clip = None
    background_clip = None
    final_clip = None
    temp_bg_image = None
    
    try:
        # 1. โหลดไฟล์เสียงพากย์วัยรุ่น
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration

        # 2. ดึงภาพการ์ตูนพื้นหลังแบบสุ่มจากคลังภาพออนไลน์ฟรี
        temp_bg_image = download_cartoon_background()

        # 3. แปลงภาพนิ่งการ์ตูนให้กลายเป็นคลิปวิดีโอตามความยาวของเสียงพากย์เป๊ะๆ
        background_clip = ImageClip(temp_bg_image).with_duration(audio_duration)

        # 4. ใส่เสียงพากย์เข้าไป
        final_clip = background_clip.with_audio(audio_clip)
        
        # 5. Export วิดีโอมาตรฐาน (30fps สำหรับ CapCut/TikTok)
        final_clip.write_videofile(
            output_video_path,
            codec="libx264",
            audio_codec="aac",
            fps=30,
            logger=None
        )
    except Exception as exc:
        raise RuntimeError(f"เกิดข้อผิดพลาดขณะประกอบวิดีโอการ์ตูน: {exc}") from exc
    finally:
        # ล้างไฟล์และปิดคลิป
        for clip in (audio_clip, background_clip, final_clip):
            try:
                if clip: clip.close()
            except: pass
            
        if temp_bg_image and os.path.exists(temp_bg_image):
            try: os.remove(temp_bg_image)
            except: pass