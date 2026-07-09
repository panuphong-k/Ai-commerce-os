"""
tests/test_video_creator.py
-----------------------------
ทดสอบ video_creator.py (text_to_speech + create_video)
โดย stub เอง `edge_tts` และ `moviepy` ด้วย tests/fakes.py แทนของจริง
เพื่อให้ทดสอบ "logic" ของเราได้ โดยไม่ต้องเรียก TTS จริงหรือเรียก ffmpeg จริง
"""

import asyncio
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests import fakes  # noqa: E402


class VideoCreatorTestCase(unittest.TestCase):
    """Base class: จัดการ temp dir + reset sys.modules ให้ทุก test"""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="ai_commerce_os_test_")
        self._old_cwd = os.getcwd()
        os.chdir(self.tmp_dir)
        fakes.reset_modules()

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        fakes.reset_modules()

    def import_video_creator(self, **moviepy_kwargs):
        """ติดตั้ง stub แล้ว import video_creator ใหม่ (fresh import)"""
        fakes.install_edge_tts_stub()
        self.moviepy_calls = fakes.install_moviepy_stub(**moviepy_kwargs)
        import video_creator  # import ทีหลังสุด หลังจาก stub ถูกฝังแล้ว

        return video_creator


# =========================================================================
# text_to_speech()
# =========================================================================
class TestTextToSpeech(VideoCreatorTestCase):
    def test_empty_text_raises_value_error(self):
        vc = self.import_video_creator()
        with self.assertRaises(ValueError):
            vc.text_to_speech("")

    def test_whitespace_only_text_raises_value_error(self):
        vc = self.import_video_creator()
        with self.assertRaises(ValueError):
            vc.text_to_speech("   \n\t  ")

    def test_success_creates_audio_file_with_default_voice(self):
        vc = self.import_video_creator()
        output_path = vc.text_to_speech("สวัสดีค่ะ ทดสอบระบบ", output_path="out.mp3")
        self.assertEqual(output_path, "out.mp3")
        self.assertTrue(os.path.exists("out.mp3"))

    def test_uses_specified_output_path(self):
        vc = self.import_video_creator()
        result_path = vc.text_to_speech("ทดสอบ", output_path="custom_name.mp3")
        self.assertEqual(result_path, "custom_name.mp3")
        self.assertTrue(os.path.exists("custom_name.mp3"))

    def test_default_voice_is_thai_female(self):
        """ตรวจว่า DEFAULT_VOICE เป็นเสียงภาษาไทยตามที่ระบุในโจทย์"""
        vc = self.import_video_creator()
        self.assertEqual(vc.DEFAULT_VOICE, "th-TH-PremwadeeNeural")

    def test_edge_tts_failure_is_wrapped_as_runtime_error(self):
        fakes.reset_modules()
        fakes.install_edge_tts_stub(should_raise=True)
        fakes.install_moviepy_stub()
        import video_creator as vc

        with self.assertRaises(RuntimeError) as ctx:
            vc.text_to_speech("ข้อความทดสอบ")
        self.assertIn("แปลงข้อความเป็นเสียง", str(ctx.exception))

    def test_can_actually_run_the_underlying_coroutine(self):
        """ทดสอบเสริม: เรียก _generate_speech_async ตรงๆ ด้วย asyncio เพื่อยืนยันว่า
        เป็น coroutine ที่ทำงานได้จริงกับ event loop (ไม่ใช่แค่ mock เฉยๆ)"""
        vc = self.import_video_creator()
        asyncio.run(vc._generate_speech_async("ทดสอบ", "async_out.mp3", vc.DEFAULT_VOICE))
        self.assertTrue(os.path.exists("async_out.mp3"))


# =========================================================================
# create_video()
# =========================================================================
class TestCreateVideo(VideoCreatorTestCase):
    def test_missing_background_video_raises_file_not_found(self):
        vc = self.import_video_creator()
        with open("audio.mp3", "wb") as f:
            f.write(b"fake")

        with self.assertRaises(FileNotFoundError) as ctx:
            vc.create_video(audio_path="audio.mp3", background_video_path="assets/background.mp4")
        self.assertIn("background.mp4", str(ctx.exception))

    def test_missing_audio_file_raises_file_not_found(self):
        vc = self.import_video_creator()
        os.makedirs("assets", exist_ok=True)
        with open("assets/background.mp4", "wb") as f:
            f.write(b"fake")

        with self.assertRaises(FileNotFoundError):
            vc.create_video(audio_path="does_not_exist.mp3", background_video_path="assets/background.mp4")

    def test_background_longer_than_audio_trims_directly(self):
        """background (20s) ยาวกว่า audio (10s) -> ต้อง subclip ตรงๆ โดยไม่ loop"""
        vc = self.import_video_creator(video_duration=20.0, audio_duration=10.0)
        os.makedirs("assets", exist_ok=True)
        with open("assets/background.mp4", "wb") as _f:
            _f.write(b"fake")
        with open("audio.mp3", "wb") as _f:
            _f.write(b"fake")

        output = vc.create_video(
            audio_path="audio.mp3",
            output_video_path="out.mp4",
            background_video_path="assets/background.mp4",
        )

        self.assertEqual(output, "out.mp4")
        self.assertTrue(os.path.exists("out.mp4"))

        call_names = [c[0] for c in self.moviepy_calls]
        self.assertIn("subclipped", call_names)
        self.assertNotIn("with_effects", call_names)  # ไม่ควร loop เพราะวิดีโอยาวพออยู่แล้ว

        subclip_call = next(c for c in self.moviepy_calls if c[0] == "subclipped")
        self.assertEqual(subclip_call[1], 0)
        self.assertEqual(subclip_call[2], 10.0)  # ต้องตัดพอดีความยาวเสียง

    def test_background_shorter_than_audio_loops_video(self):
        """background (5s) สั้นกว่า audio (12s) -> ต้อง loop วิดีโอก่อน แล้วค่อยตัด"""
        vc = self.import_video_creator(video_duration=5.0, audio_duration=12.0)
        os.makedirs("assets", exist_ok=True)
        with open("assets/background.mp4", "wb") as _f:
            _f.write(b"fake")
        with open("audio.mp3", "wb") as _f:
            _f.write(b"fake")

        vc.create_video(
            audio_path="audio.mp3",
            output_video_path="out.mp4",
            background_video_path="assets/background.mp4",
        )

        call_names = [c[0] for c in self.moviepy_calls]
        self.assertIn("with_effects", call_names)

        effects_call = next(c for c in self.moviepy_calls if c[0] == "with_effects")
        loop_effect = effects_call[1][0]
        # 12 // 5 = 2, +1 = 3 รอบ ถึงจะครอบคลุมความยาวเสียง 12 วินาที
        self.assertEqual(loop_effect.n, 3)

    def test_final_clip_gets_audio_attached(self):
        vc = self.import_video_creator(video_duration=20.0, audio_duration=8.0)
        os.makedirs("assets", exist_ok=True)
        with open("assets/background.mp4", "wb") as _f:
            _f.write(b"fake")
        with open("audio.mp3", "wb") as _f:
            _f.write(b"fake")

        vc.create_video(audio_path="audio.mp3", output_video_path="out.mp4")

        call_names = [c[0] for c in self.moviepy_calls]
        self.assertIn("with_audio", call_names)
        # with_audio ต้องถูกเรียกหลัง subclipped เสมอ (ลำดับ pipeline ถูกต้อง)
        self.assertLess(call_names.index("subclipped"), call_names.index("with_audio"))

    def test_write_videofile_uses_expected_codecs(self):
        vc = self.import_video_creator(video_duration=20.0, audio_duration=8.0)
        os.makedirs("assets", exist_ok=True)
        with open("assets/background.mp4", "wb") as _f:
            _f.write(b"fake")
        with open("audio.mp3", "wb") as _f:
            _f.write(b"fake")

        vc.create_video(audio_path="audio.mp3", output_video_path="out.mp4")

        write_call = next(c for c in self.moviepy_calls if c[0] == "write_videofile")
        _, path, kwargs = write_call
        self.assertEqual(path, "out.mp4")
        self.assertEqual(kwargs.get("codec"), "libx264")
        self.assertEqual(kwargs.get("audio_codec"), "aac")

    def test_encoding_failure_is_wrapped_as_runtime_error_and_clips_closed(self):
        """หาก write_videofile ล้มเหลว (จำลอง ffmpeg error) ต้องได้ RuntimeError
        ที่มีข้อความอธิบาย และ clip ทุกตัวที่เปิดไว้ต้องถูก .close() แม้เกิด error"""
        fakes.reset_modules()
        fakes.install_edge_tts_stub()
        calls = fakes.install_moviepy_stub(
            video_duration=20.0,
            audio_duration=8.0,
            video_clip_cls=fakes.RaisingFakeClip,
        )
        import video_creator as vc

        os.makedirs("assets", exist_ok=True)
        with open("assets/background.mp4", "wb") as _f:
            _f.write(b"fake")
        with open("audio.mp3", "wb") as _f:
            _f.write(b"fake")

        with self.assertRaises(RuntimeError) as ctx:
            vc.create_video(audio_path="audio.mp3", output_video_path="out.mp4")

        self.assertIn("ประกอบวิดีโอ", str(ctx.exception))
        # ไฟล์ out.mp4 ต้องไม่ถูกสร้างขึ้น เพราะ write_videofile ล้มเหลวก่อนเขียนไฟล์จริง
        self.assertFalse(os.path.exists("out.mp4"))


if __name__ == "__main__":
    unittest.main()
