# video_creator.py
import asyncio
import os
import random
import math
import edge_tts
from moviepy import AudioFileClip, VideoClip

DEFAULT_VOICE = "th-TH-PremwadeeNeural"

async def _generate_speech_async(text: str, output_path: str, voice: str) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(output_path)

def text_to_speech(script_text: str, output_path: str, voice: str = DEFAULT_VOICE) -> None:
    try:
        asyncio.run(_generate_speech_async(script_text, output_path, voice))
    except Exception as exc:
        raise RuntimeError(f"เกิดข้อผิดพลาดในการแปลงเสียงพากย์: {exc}") from exc

def make_gradient_frame(t, width=1080, height=1920):
    """สร้างเฟรมวิดีโอไล่เฉดสีแนวตั้ง (9:16) ที่ขยับเคลื่อนไหวตามเวลา (t)"""
    import numpy as np
    
    # กำหนดคู่สีฐาน (RGB) สไตล์พาสเทล TikTok
    # เฟรมจะขยับสีไปเรื่อยๆ ตามฟังก์ชัน Sine ของเวลา t
    shift = math.sin(t * 0.5) * 30
    
    r1, g1, b1 = int(255 - shift), int(210 + shift), int(210)
    r2, g2, b2 = int(210), int(210 - shift), int(255 + shift)
    
    # สร้างเมทริกซ์ Gradient จากบนลงล่าง
    grid = np.linspace(0, 1, height)[:, None]
    
    r = r1 + (r2 - r1) * grid
    g = g1 + (g2 - g1) * grid
    b = b1 + (b2 - b1) * grid
    
    # รวมแชนเนลสีและขยายให้เต็มความกว้าง
    frame = np.dstack((r, g, b)).astype(np.uint8)
    frame = np.repeat(frame, width, axis=1)
    
    return frame

def create_video(audio_path: str, output_video_path: str) -> None:
    """สร้างวิดีโอภาพเคลื่อนไหว Gradient พร้อมใส่เสียงพากย์ อัตโนมัติโดยไม่ต้องใช้ไฟล์นอก"""
    audio_clip = None
    background_clip = None
    final_clip = None
    
    try:
        # 1. โหลดไฟล์เสียงเพื่อเช็คความยาว
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration

        # 2. สร้างคลิปวิดีโอภาพเคลื่อนไหวด้วยการเขียนฟังก์ชันวาดเฟรมทีละวิตามความยาวเสียง
        background_clip = VideoClip(lambda t: make_gradient_frame(t), duration=audio_duration)

        # 3. รวมเสียงพากย์เข้ากับวิดีโอที่สร้างขึ้น
        final_clip = background_clip.with_audio(audio_clip)
        
        # 4. Export วิดีโอมาตรฐานสากล (CapCut นำเข้าใช้งานได้ทันที)
        final_clip.write_videofile(
            output_video_path,
            codec="libx264",
            audio_codec="aac",
            fps=30,  # 30 fps สแตนดาร์ดสำหรับ CapCut/TikTok
            logger=None
        )
    except Exception as exc:
        raise RuntimeError(f"เกิดข้อผิดพลาดขณะประกอบวิดีโอ: {exc}") from exc
    finally:
        for clip in (audio_clip, background_clip, final_clip):
            try:
                if clip: clip.close()
            except: pass