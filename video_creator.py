"""
video_creator.py
-----------------
โมดูลสำหรับจัดการ "เสียง" และ "วิดีโอ"

ประกอบด้วย 2 ฟังก์ชันหลัก:
1. text_to_speech()  -> แปลงบทพากย์เสียง (ข้อความ) เป็นไฟล์เสียง .mp3 ภาษาไทย ด้วย edge-tts
2. create_video()    -> นำไฟล์เสียงที่ได้ มารวมเข้ากับวิดีโอพื้นหลัง (assets/background.mp4)
                        โดยตัดความยาววิดีโอให้พอดีกับความยาวเสียงพากย์อัตโนมัติ
"""

import asyncio
import os

import edge_tts
from moviepy import AudioFileClip, VideoFileClip, vfx

# -----------------------------------------------------------------------
# ค่าคงที่ที่ใช้ในโมดูลนี้
# -----------------------------------------------------------------------
# เสียงพากย์ภาษาไทยที่แนะนำจาก edge-tts
# th-TH-PremwadeeNeural = เสียงผู้หญิง, th-TH-NiwatNeural = เสียงผู้ชาย
DEFAULT_VOICE = "th-TH-PremwadeeNeural"

BACKGROUND_VIDEO_PATH = "assets/background.mp4"


async def _generate_speech_async(text: str, output_path: str, voice: str) -> None:
    """
    ฟังก์ชันภายใน (private) สำหรับเรียก edge-tts แบบ async
    เนื่องจากไลบรารี edge-tts ถูกออกแบบมาให้ทำงานแบบ asynchronous
    """
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(output_path)


def text_to_speech(
    script_text: str,
    output_path: str = "output_audio.mp3",
    voice: str = DEFAULT_VOICE,
) -> str:
    """
    แปลงข้อความบทพากย์เสียงให้เป็นไฟล์เสียง .mp3 ภาษาไทย

    Args:
        script_text: บทพากย์เสียงที่ได้จาก Gemini
        output_path: พาธที่ต้องการบันทึกไฟล์เสียงผลลัพธ์
        voice: ชื่อเสียงพากย์ของ edge-tts (ค่าเริ่มต้น th-TH-PremwadeeNeural)

    Returns:
        พาธของไฟล์เสียงที่สร้างเสร็จแล้ว

    Raises:
        ValueError: หากข้อความว่างเปล่า
        RuntimeError: หากเกิดข้อผิดพลาดระหว่างเรียก edge-tts
    """
    if not script_text or not script_text.strip():
        raise ValueError("ไม่สามารถแปลงเสียงได้ เนื่องจากบทพากย์เสียงว่างเปล่า")

    try:
        # ใช้ asyncio.run() เพื่อเรียกฟังก์ชัน async จาก context ปกติ (sync)
        # ซึ่งเหมาะกับการใช้งานใน Streamlit ที่ทำงานแบบ script เรียงบรรทัด
        asyncio.run(_generate_speech_async(script_text, output_path, voice))
    except Exception as exc:  # noqa: BLE001 - ต้องการดักทุก error จาก edge-tts มาแปลงเป็นข้อความที่เข้าใจง่าย
        raise RuntimeError(f"เกิดข้อผิดพลาดขณะแปลงข้อความเป็นเสียง: {exc}") from exc

    return output_path


def create_video(
    audio_path: str,
    output_video_path: str = "final_video.mp4",
    background_video_path: str = BACKGROUND_VIDEO_PATH,
) -> str:
    """
    นำไฟล์เสียงพากย์มารวมกับวิดีโอพื้นหลัง โดยตัดความยาววิดีโอให้พอดีกับเสียง

    ขั้นตอนการทำงาน:
    1. ตรวจสอบว่ามีไฟล์วิดีโอพื้นหลังอยู่จริงหรือไม่ (ป้องกัน error กรณีลืมอัปโหลด asset)
    2. โหลดไฟล์เสียงและวิดีโอ
    3. ตัด (subclip) วิดีโอพื้นหลังให้มีความยาวเท่ากับเสียงพากย์พอดี
       - ถ้าวิดีโอพื้นหลังสั้นกว่าเสียงพากย์ จะเล่นวนซ้ำ (loop) วิดีโอจนครบความยาวเสียง
    4. ใส่เสียงพากย์เข้าไปในวิดีโอ แล้ว export ออกมาเป็นไฟล์ .mp4

    Args:
        audio_path: พาธไฟล์เสียงพากย์ (.mp3) ที่ได้จาก text_to_speech()
        output_video_path: พาธที่ต้องการบันทึกวิดีโอผลลัพธ์
        background_video_path: พาธของวิดีโอพื้นหลัง (ค่าเริ่มต้น assets/background.mp4)

    Returns:
        พาธของไฟล์วิดีโอที่สร้างเสร็จแล้ว

    Raises:
        FileNotFoundError: หากหาไฟล์วิดีโอพื้นหลังไม่เจอ
        RuntimeError: หากเกิดข้อผิดพลาดระหว่างการประกอบวิดีโอ
    """
    # --- ป้องกัน Error กรณีหาไฟล์ background.mp4 ไม่เจอ ---
    if not os.path.exists(background_video_path):
        raise FileNotFoundError(
            f"ไม่พบไฟล์วิดีโอพื้นหลังที่ '{background_video_path}' "
            "กรุณาอัปโหลดไฟล์วิดีโอพื้นหลังไว้ในโฟลเดอร์ assets/ ก่อนเริ่มสร้างคลิป"
        )

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"ไม่พบไฟล์เสียงพากย์ที่ '{audio_path}'")

    audio_clip = None
    background_clip = None
    final_clip = None

    try:
        audio_clip = AudioFileClip(audio_path)
        background_clip = VideoFileClip(background_video_path)

        audio_duration = audio_clip.duration

        # --- ปรับความยาววิดีโอพื้นหลังให้พอดีกับความยาวเสียงพากย์ ---
        if background_clip.duration >= audio_duration:
            # วิดีโอพื้นหลังยาวพอ -> ตัดให้สั้นลงเท่ากับความยาวเสียง
            final_clip = background_clip.subclipped(0, audio_duration)
        else:
            # วิดีโอพื้นหลังสั้นกว่าเสียงพากย์ -> เล่นวนซ้ำจนครบความยาวเสียง
            loop_count = int(audio_duration // background_clip.duration) + 1
            looped_clip = background_clip.with_effects([vfx.Loop(n=loop_count)])
            final_clip = looped_clip.subclipped(0, audio_duration)

        # --- ใส่เสียงพากย์เข้าไปในวิดีโอ (แทนที่เสียงเดิม ถ้ามี) ---
        final_clip = final_clip.with_audio(audio_clip)

        # --- Export ไฟล์วิดีโอผลลัพธ์ ---
        final_clip.write_videofile(
            output_video_path,
            codec="libx264",
            audio_codec="aac",
            fps=30,
            logger=None,  # ปิด progress bar ของ moviepy ไม่ให้รก log ของ Streamlit
        )

    except FileNotFoundError:
        raise
    except Exception as exc:  # noqa: BLE001 - ดัก error ทั้งหมดจาก moviepy มาแปลงเป็นข้อความที่เข้าใจง่าย
        raise RuntimeError(f"เกิดข้อผิดพลาดขณะประกอบวิดีโอ: {exc}") from exc
    finally:
        # ปิดไฟล์ทุกตัวเสมอ เพื่อคืน resource แม้เกิด error ระหว่างทาง
        for clip in (audio_clip, background_clip, final_clip):
            try:
                if clip is not None:
                    clip.close()
            except Exception:  # noqa: BLE001 - การปิดไฟล์ล้มเหลวไม่ควรทำให้โปรแกรมล่ม
                pass

    return output_video_path
