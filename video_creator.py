import asyncio
import os
import random
import edge_tts
import requests
from moviepy import AudioFileClip, ImageClip

# ใช้เสียงผู้หญิง th-TH-PremwadeeNeural ที่ดูเป็นวัยรุ่นและธรรมชาติที่สุด
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
    """สุ่มลิงก์ภาพการ์ตูน/ภาพวาดมินิมอลพาสเทลจาก Unsplash สำหรับทำพื้นหลังแนวตั้ง 9:16"""
    backup_urls = [
        "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe", # Pastel abstract
        "https://images.unsplash.com/photo-1579546929518-9e396f3cc809", # Fluid Gradient
        "https://images.unsplash.com/photo-1604871000636-074fa5117945", # Minimal Art
        "https://images.unsplash.com/photo-1563089145-599997674d42", # Neon Pop
    ]
    random_url = random.choice(backup_urls) + "?auto=format&fit=crop&w=1080&h=1920"
    
    temp_bg_path = "temp_cartoon_bg.jpg"
    try:
        response = requests.get(random_url, timeout=10)
        if response.status_code == 200:
            with open(temp_bg_path, "wb") as f:
                f.write(response.content)
            return temp_bg_path
    except Exception:
        pass
        
    # หากดาวน์โหลดจากเน็ตไม่ได้ ให้สร้างภาพสีชมพูพาสเทลขึ้นมาเองเป็นตัวสำรอง
    from PIL import Image
    img = Image.new("RGB", (1080, 1920), color=(255, 210, 220))
    img.save(temp_bg_path)
    return temp_bg_path

def create_video(audio_path: str, output_video_path: str) -> None:
    """สร้างวิดีโอจากภาพการ์ตูนพื้นหลัง ยืดเวลาตามความยาวของเสียงพากย์"""
    audio_clip = None
    background_clip = None
    final_clip = None
    temp_bg_image = None
    
    try:
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration

        # สุ่มดึงภาพการ์ตูน/อาร์ตพาสเทลมาใช้งาน
        temp_bg_image = download_cartoon_background()

        # แปลงภาพนิ่งให้เป็นคลิปวิดีโอตามความยาวเสียงเป๊ะๆ
        background_clip = ImageClip(temp_bg_image).with_duration(audio_duration)

        final_clip = background_clip.with_audio(audio_clip)
        final_clip.write_videofile(
            output_video_path,
            codec="libx264",
            audio_codec="aac",
            fps=30,
            logger=None
        )
    except Exception as exc:
        raise RuntimeError(f"เกิดข้อผิดพลาดขณะประกอบวิดีโอ: {exc}") from exc
    finally:
        for clip in (audio_clip, background_clip, final_clip):
            try:
                if clip:
                    clip.close()
            except Exception:
                pass
            
        if temp_bg_image and os.path.exists(temp_bg_image):
            try:
                os.remove(temp_bg_image)
            except OSError:
                pass