"""
tests/fakes.py
---------------
รวมฟังก์ชันสำหรับสร้าง "fake module" ของไลบรารีภายนอกทั้งหมดที่โปรเจกต์นี้ใช้
(edge_tts, moviepy, google-genai, streamlit) แล้วฝังลงใน sys.modules

เหตุผลที่ต้องทำแบบนี้:
- โปรเจกต์นี้ตั้งใจให้รันบน Streamlit Community Cloud ซึ่งจะติดตั้ง library
  จริงจาก requirements.txt ให้เอง แต่ในสภาพแวดล้อมทดสอบ (CI / เครื่อง dev
  ที่ยังไม่ได้ pip install หรือไม่มีอินเทอร์เน็ต) เราต้องการทดสอบ "logic"
  ของโค้ดเรา (การจัดการ error, การคำนวณความยาววิดีโอ, การประกอบ prompt ฯลฯ)
  โดยไม่ต้องเรียก TikTok/Gemini/ffmpeg จริง และไม่ต้องพึ่งการติดตั้ง library หนักๆ

ทุกฟังก์ชัน install_*_stub() จะคืนค่า "calls" (list) ที่บันทึกไว้ว่ามีการเรียก
ฟังก์ชัน/เมธอดอะไรบ้าง ด้วย argument อะไร เพื่อให้ test case ใช้ assert ได้
"""

import sys
import types


# =========================================================================
# 1) Fake edge_tts
# =========================================================================
def install_edge_tts_stub(should_raise: bool = False, calls: list | None = None) -> list:
    """ติดตั้ง fake `edge_tts` module ลงใน sys.modules"""
    calls = calls if calls is not None else []
    module = types.ModuleType("edge_tts")

    class FakeCommunicate:
        def __init__(self, text, voice):
            calls.append(("Communicate.__init__", text, voice))
            self.text = text
            self.voice = voice

        async def save(self, path):
            calls.append(("Communicate.save", path))
            if should_raise:
                raise RuntimeError("simulated edge-tts network failure")
            with open(path, "wb") as f:
                f.write(b"FAKE_AUDIO_BYTES")

    module.Communicate = FakeCommunicate
    sys.modules["edge_tts"] = module
    return calls


# =========================================================================
# 2) Fake moviepy
# =========================================================================
class FakeLoop:
    """เลียนแบบ moviepy.vfx.Loop(n=...)"""

    def __init__(self, n=1):
        self.n = n


class FakeClip:
    """
    เลียนแบบพฤติกรรมพื้นฐานที่โค้ดของเราใช้จาก VideoClip/AudioClip ใน moviepy:
    .duration, .subclipped(), .with_effects(), .with_audio(), .write_videofile(), .close()

    ทุกเมธอดคืน FakeClip ใหม่ (out-place) เหมือน moviepy v2 จริง และบันทึกการเรียกไว้ใน self.calls
    (ใช้ list เดียวกันร่วมกันทุก object เพื่อให้ตรวจสอบลำดับการเรียกได้)
    """

    def __init__(self, duration, calls, kind="video"):
        self.duration = duration
        self.calls = calls
        self.kind = kind
        self.closed = False

    def subclipped(self, start_time=0, end_time=None):
        self.calls.append(("subclipped", start_time, end_time))
        new_duration = (end_time if end_time is not None else self.duration) - start_time
        return type(self)(new_duration, self.calls, kind=self.kind)

    def with_effects(self, effects):
        self.calls.append(("with_effects", effects))
        loop_effect = effects[0]
        n = getattr(loop_effect, "n", 1)
        return type(self)(self.duration * n, self.calls, kind=self.kind)

    def with_audio(self, audio_clip):
        self.calls.append(("with_audio", audio_clip))
        new_clip = type(self)(self.duration, self.calls, kind=self.kind)
        new_clip.audio = audio_clip
        return new_clip

    def write_videofile(self, path, **kwargs):
        self.calls.append(("write_videofile", path, kwargs))
        # จำลองการเขียนไฟล์จริงลงดิสก์ เพื่อให้ทดสอบ downstream (เช่น os.path.exists) ได้
        with open(path, "wb") as f:
            f.write(b"FAKE_VIDEO_BYTES")

    def close(self):
        self.closed = True
        self.calls.append(("close", self.kind))


class RaisingFakeClip(FakeClip):
    """FakeClip ที่จำลองการ error ตอน write_videofile (เช่น ffmpeg ล้มเหลว)"""

    def write_videofile(self, path, **kwargs):
        self.calls.append(("write_videofile:will_raise", path))
        raise OSError("simulated ffmpeg encoding failure")


def install_moviepy_stub(
    video_duration: float = 20.0,
    audio_duration: float = 10.0,
    video_clip_cls=FakeClip,
    calls: list | None = None,
) -> list:
    """
    ติดตั้ง fake `moviepy` module ลงใน sys.modules

    Args:
        video_duration: ความยาว (วินาที) ของวิดีโอพื้นหลังจำลอง
        audio_duration: ความยาว (วินาที) ของไฟล์เสียงจำลอง
        video_clip_cls: class ที่จะใช้สร้าง VideoFileClip (ใช้ RaisingFakeClip เพื่อจำลอง error ได้)
        calls: list สำหรับบันทึกการเรียกทั้งหมด (ใช้ตรวจสอบใน assert)
    """
    calls = calls if calls is not None else []
    module = types.ModuleType("moviepy")

    def VideoFileClip(path):
        calls.append(("VideoFileClip", path))
        return video_clip_cls(video_duration, calls, kind="video")

    def AudioFileClip(path):
        calls.append(("AudioFileClip", path))
        return FakeClip(audio_duration, calls, kind="audio")

    module.VideoFileClip = VideoFileClip
    module.AudioFileClip = AudioFileClip
    module.vfx = types.SimpleNamespace(Loop=FakeLoop)

    sys.modules["moviepy"] = module
    return calls


# =========================================================================
# 3) Fake google-genai SDK (from google import genai / from google.genai import types)
# =========================================================================
def install_google_genai_stub(
    response_text: str = "สวัสดีค่ะ นี่คือสคริปต์ตัวอย่าง",
    raise_on_call: bool = False,
    calls: list | None = None,
) -> list:
    """ติดตั้ง fake `google.genai` module ลงใน sys.modules"""
    calls = calls if calls is not None else []

    google_module = types.ModuleType("google")
    genai_module = types.ModuleType("google.genai")
    genai_types_module = types.ModuleType("google.genai.types")

    class FakeGenerateContentConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeResponse:
        def __init__(self, text):
            self.text = text

    class FakeModels:
        def generate_content(self, model, contents, config=None):
            calls.append(("generate_content", model, contents, config))
            if raise_on_call:
                raise RuntimeError("simulated Gemini API failure")
            return FakeResponse(response_text)

    class FakeClient:
        def __init__(self, api_key=None):
            calls.append(("Client.__init__", api_key))
            self.models = FakeModels()

    genai_module.Client = FakeClient
    genai_types_module.GenerateContentConfig = FakeGenerateContentConfig
    genai_module.types = genai_types_module

    google_module.genai = genai_module

    sys.modules["google"] = google_module
    sys.modules["google.genai"] = genai_module
    sys.modules["google.genai.types"] = genai_types_module
    return calls


# =========================================================================
# 4) Fake streamlit
# =========================================================================
class FakeStatus:
    """เลียนแบบ context manager ที่คืนจาก st.status(...)"""

    def __init__(self, label, expanded=False):
        self.label = label
        self.state = "running"
        self.expanded = expanded

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False  # ไม่กลืน exception ใดๆ ปล่อยให้หลุดออกไปตามปกติ

    def update(self, label=None, state=None, expanded=None):
        if label is not None:
            self.label = label
        if state is not None:
            self.state = state
        if expanded is not None:
            self.expanded = expanded


class FakeSecrets(dict):
    """เลียนแบบ st.secrets ซึ่งมีพฤติกรรมคล้าย dict (รองรับ .get())"""


def install_streamlit_stub(
    text_input_value: str = "",
    text_area_value: str = "",
    button_value: bool = False,
    secrets: dict | None = None,
    secrets_raises: bool = False,
    calls: list | None = None,
):
    """
    ติดตั้ง fake `streamlit` module ลงใน sys.modules
    ครอบคลุมทุกฟังก์ชันที่ app.py เรียกใช้ตอน import (module-level) และในปุ่มกด

    Returns:
        (module, calls, errors, warnings) - errors/warnings คือข้อความที่ถูกส่งเข้า
        st.error(...) / st.warning(...) ตามลำดับ เอาไว้ assert เนื้อหาข้อความได้
    """
    calls = calls if calls is not None else []
    errors: list = []
    warnings: list = []
    successes: list = []

    module = types.ModuleType("streamlit")

    def _recorder(name, sink=None):
        def _fn(*args, **kwargs):
            calls.append((name, args, kwargs))
            if sink is not None and args:
                sink.append(args[0])
        return _fn

    module.set_page_config = _recorder("set_page_config")
    module.title = _recorder("title")
    module.caption = _recorder("caption")
    module.divider = _recorder("divider")
    module.subheader = _recorder("subheader")
    module.write = _recorder("write")
    module.video = _recorder("video")
    module.success = _recorder("success", sink=successes)
    module.warning = _recorder("warning", sink=warnings)
    module.error = _recorder("error", sink=errors)

    def text_input(label, **kwargs):
        calls.append(("text_input", label, kwargs))
        return text_input_value

    def text_area(label, **kwargs):
        calls.append(("text_area", label, kwargs))
        return text_area_value

    def button(label, **kwargs):
        calls.append(("button", label, kwargs))
        return button_value

    def download_button(**kwargs):
        calls.append(("download_button", kwargs))

    def status(label, **kwargs):
        calls.append(("status", label, kwargs))
        return FakeStatus(label, kwargs.get("expanded", False))

    module.text_input = text_input
    module.text_area = text_area
    module.button = button
    module.download_button = download_button
    module.status = status

    if secrets_raises:
        class RaisingSecrets:
            def get(self, *a, **kw):
                raise RuntimeError("simulated: no secrets.toml configured")

        module.secrets = RaisingSecrets()
    else:
        module.secrets = FakeSecrets(secrets or {})

    sys.modules["streamlit"] = module
    return module, calls, errors, warnings


# =========================================================================
# Utility: ล้าง module ของโปรเจกต์ + fake libraries ออกจาก sys.modules
# =========================================================================
PROJECT_MODULES = ["app", "prompts", "video_creator"]
FAKE_LIBRARY_MODULES = [
    "streamlit",
    "edge_tts",
    "moviepy",
    "google",
    "google.genai",
    "google.genai.types",
]


def reset_modules():
    """ลบ module ของโปรเจกต์และ fake library ทั้งหมดออกจาก sys.modules
    เพื่อบังคับให้ import ครั้งถัดไปเป็นการรันไฟล์ใหม่ทั้งหมด (สำคัญมากสำหรับ app.py
    เพราะมันมี top-level code ที่ต้องรันใหม่ทุกครั้งที่เปลี่ยน stub)"""
    for name in PROJECT_MODULES + FAKE_LIBRARY_MODULES:
        sys.modules.pop(name, None)
