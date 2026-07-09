"""
tests/test_app.py
-------------------
ทดสอบ app.py โดย stub `streamlit`, `google.genai`, `edge_tts`, `moviepy` ทั้งหมด
เนื่องจาก app.py มีโค้ดระดับ module (module-level) ที่รันทันทีตอน import
(เช่น st.set_page_config, st.text_input, st.button) จึงต้อง reset และ import
โมดูลใหม่ทุกครั้งที่เปลี่ยนค่า stub (เช่น เปลี่ยนค่าที่ผู้ใช้กรอก หรือค่าปุ่มกด)
"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests import fakes  # noqa: E402


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="ai_commerce_os_test_")
        self._old_cwd = os.getcwd()
        os.chdir(self.tmp_dir)
        fakes.reset_modules()

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        fakes.reset_modules()


# =========================================================================
# generate_script()
# =========================================================================
class TestGenerateScript(AppTestCase):
    def _import_app(self, **kwargs):
        st_kwargs = {
            "text_input_value": kwargs.pop("text_input_value", ""),
            "text_area_value": kwargs.pop("text_area_value", ""),
            "button_value": kwargs.pop("button_value", False),  # False = ไม่ trigger UI branch ตอน import
            "secrets": kwargs.pop("secrets", {"GEMINI_API_KEY": "fake-api-key-123"}),
            "secrets_raises": kwargs.pop("secrets_raises", False),
        }
        self.st_module, self.st_calls, self.st_errors, self.st_warnings = fakes.install_streamlit_stub(**st_kwargs)
        self.genai_calls = fakes.install_google_genai_stub(**kwargs)
        fakes.install_edge_tts_stub()
        fakes.install_moviepy_stub()

        import app  # ต้อง import "หลัง" ติดตั้ง stub ครบทุกตัวเสมอ

        return app

    def test_returns_script_text_from_gemini(self):
        app = self._import_app(response_text="Hook สุดปัง Agitate เจ็บจี๊ด Solution เจ๋ง CTA กดเลย")
        result = app.generate_script("เซรั่มลดสิว", "หน้ามันเยิ้ม")
        self.assertEqual(result, "Hook สุดปัง Agitate เจ็บจี๊ด Solution เจ๋ง CTA กดเลย")

    def test_strips_whitespace_from_response(self):
        app = self._import_app(response_text="   มีช่องว่างรอบข้อความ   \n")
        result = app.generate_script("สินค้า", "ปัญหา")
        self.assertEqual(result, "มีช่องว่างรอบข้อความ")

    def test_passes_correct_model_and_system_prompt_to_gemini(self):
        app = self._import_app(response_text="สคริปต์")
        app.generate_script("สินค้า A", "ปัญหา A")

        call = next(c for c in self.genai_calls if c[0] == "generate_content")
        _, model, contents, config = call
        self.assertEqual(model, app.GEMINI_MODEL_NAME)
        self.assertIn("สินค้า A", contents)
        self.assertIn("ปัญหา A", contents)
        self.assertEqual(config.kwargs.get("system_instruction"), app.SYSTEM_PROMPT)

    def test_client_initialized_with_api_key_from_secrets(self):
        app = self._import_app(response_text="สคริปต์", secrets={"GEMINI_API_KEY": "MY-SECRET-KEY"})
        app.generate_script("สินค้า", "ปัญหา")

        client_call = next(c for c in self.genai_calls if c[0] == "Client.__init__")
        self.assertEqual(client_call[1], "MY-SECRET-KEY")

    def test_missing_api_key_raises_runtime_error(self):
        app = self._import_app(response_text="สคริปต์", secrets={})
        with self.assertRaises(RuntimeError) as ctx:
            app.generate_script("สินค้า", "ปัญหา")
        self.assertIn("GEMINI_API_KEY", str(ctx.exception))

    def test_secrets_access_exception_is_handled_gracefully(self):
        """หาก st.secrets เข้าถึงไม่ได้เลย (ยังไม่เคยตั้งค่าอะไรบน Streamlit Cloud)
        ต้องได้ RuntimeError ที่มีข้อความอธิบายชัดเจน ไม่ใช่ exception ดิบๆ หลุดออกไป"""
        app = self._import_app(response_text="สคริปต์", secrets_raises=True)
        with self.assertRaises(RuntimeError) as ctx:
            app.generate_script("สินค้า", "ปัญหา")
        self.assertIn("GEMINI_API_KEY", str(ctx.exception))

    def test_empty_response_from_gemini_raises_runtime_error(self):
        app = self._import_app(response_text="")
        with self.assertRaises(RuntimeError) as ctx:
            app.generate_script("สินค้า", "ปัญหา")
        self.assertIn("ไม่ส่งข้อความสคริปต์กลับมา", str(ctx.exception))

    def test_whitespace_only_response_from_gemini_raises_runtime_error(self):
        app = self._import_app(response_text="   \n  ")
        with self.assertRaises(RuntimeError):
            app.generate_script("สินค้า", "ปัญหา")

    def test_gemini_api_failure_propagates_as_exception(self):
        app = self._import_app(raise_on_call=True)
        with self.assertRaises(RuntimeError):
            app.generate_script("สินค้า", "ปัญหา")


# =========================================================================
# UI-level: การกรอกข้อมูลไม่ครบต้องแสดง warning และไม่เรียก pipeline ใดๆ
# =========================================================================
class TestAppUIBranches(AppTestCase):
    def test_import_with_button_not_pressed_does_not_trigger_pipeline(self):
        """สถานะปกติตอนเปิดหน้าเว็บครั้งแรก (ยังไม่กดปุ่ม) ต้องไม่มี error/warning ใดๆ"""
        st_module, calls, errors, warnings = fakes.install_streamlit_stub(
            button_value=False,
            secrets={"GEMINI_API_KEY": "fake-key"},
        )
        fakes.install_google_genai_stub(response_text="สคริปต์")
        fakes.install_edge_tts_stub()
        fakes.install_moviepy_stub()

        import app  # noqa: F401

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_pressing_button_with_empty_inputs_shows_warning(self):
        """กดปุ่มโดยไม่กรอกชื่อสินค้า/ปัญหาลูกค้า ต้องเห็น warning และไม่เรียก Gemini"""
        st_module, calls, errors, warnings = fakes.install_streamlit_stub(
            text_input_value="",
            text_area_value="",
            button_value=True,
            secrets={"GEMINI_API_KEY": "fake-key"},
        )
        genai_calls = fakes.install_google_genai_stub(response_text="สคริปต์")
        fakes.install_edge_tts_stub()
        fakes.install_moviepy_stub()

        import app  # noqa: F401

        self.assertEqual(len(warnings), 1)
        self.assertIn("กรุณากรอก", warnings[0])
        # ต้องไม่มีการเรียก Gemini เลย เพราะข้อมูลไม่ครบ
        self.assertFalse(any(c[0] == "generate_content" for c in genai_calls))

    def test_full_pipeline_success_shows_video_and_download_button(self):
        """Happy path เต็มรูปแบบ: กรอกครบ + กดปุ่ม -> ต้องได้วิดีโอและปุ่มดาวน์โหลด ไม่มี error"""
        os.makedirs("assets", exist_ok=True)
        with open("assets/background.mp4", "wb") as f:
            f.write(b"fake background video")

        st_module, calls, errors, warnings = fakes.install_streamlit_stub(
            text_input_value="เซรั่มลดสิว",
            text_area_value="หน้ามันเยิ้มเป็นสิวบ่อย",
            button_value=True,
            secrets={"GEMINI_API_KEY": "fake-key"},
        )
        fakes.install_google_genai_stub(response_text="Hook Agitate Solution CTA แบบเต็ม")
        fakes.install_edge_tts_stub()
        fakes.install_moviepy_stub(video_duration=30.0, audio_duration=15.0)

        import app  # noqa: F401

        self.assertEqual(errors, [])
        call_names = [c[0] for c in calls]
        self.assertIn("video", call_names)
        self.assertIn("download_button", call_names)

    def test_missing_background_video_shows_friendly_error(self):
        """ไม่มี assets/background.mp4 -> ต้องเห็น error สวยงามที่พูดถึง background.mp4 ชัดเจน"""
        st_module, calls, errors, warnings = fakes.install_streamlit_stub(
            text_input_value="เซรั่มลดสิว",
            text_area_value="หน้ามันเยิ้มเป็นสิวบ่อย",
            button_value=True,
            secrets={"GEMINI_API_KEY": "fake-key"},
        )
        fakes.install_google_genai_stub(response_text="สคริปต์")
        fakes.install_edge_tts_stub()
        fakes.install_moviepy_stub()
        # หมายเหตุ: ไม่สร้าง assets/background.mp4 เลย เพื่อจำลองว่าลืมอัปโหลด asset

        import app  # noqa: F401

        self.assertEqual(len(errors), 1)
        self.assertIn("background.mp4", errors[0])

    def test_concurrent_runs_use_unique_filenames(self):
        """จำลองผู้ใช้ 2 คนกดปุ่มพร้อมกัน (import app 2 รอบ) -> ชื่อไฟล์วิดีโอ/เสียงต้องไม่ซ้ำกัน
        เพื่อป้องกัน race condition ที่ผู้ใช้คนหนึ่งไปทับไฟล์ของอีกคนหนึ่ง"""
        os.makedirs("assets", exist_ok=True)
        with open("assets/background.mp4", "wb") as f:
            f.write(b"fake")

        video_paths_seen = []

        for _ in range(2):
            fakes.reset_modules()
            st_module, calls, errors, warnings = fakes.install_streamlit_stub(
                text_input_value="สินค้า",
                text_area_value="ปัญหา",
                button_value=True,
                secrets={"GEMINI_API_KEY": "fake-key"},
            )
            fakes.install_google_genai_stub(response_text="สคริปต์")
            fakes.install_edge_tts_stub()
            fakes.install_moviepy_stub(video_duration=30.0, audio_duration=10.0)

            import app  # noqa: F401

            video_call = next(c for c in calls if c[0] == "video")
            video_paths_seen.append(video_call[1][0])  # args[0] ของ st.video(path)

        self.assertEqual(len(set(video_paths_seen)), 2, "ชื่อไฟล์วิดีโอของแต่ละรอบต้องไม่ซ้ำกัน")


if __name__ == "__main__":
    unittest.main()
