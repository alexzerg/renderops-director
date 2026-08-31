import base64
import shutil

import pytest

from app.render_executor import execute_render_fix


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_canary_executes_real_ffmpeg_and_returns_webm() -> None:
    result = execute_render_fix("canary")
    content = base64.b64decode(result.media_base64)
    assert result.exit_code == 0
    assert result.frames_processed == 5
    assert result.duration_ms > 0
    assert result.output_bytes == len(content)
    assert result.output_bytes > 10_000
    assert result.media_mime == "video/webm"
    assert content.startswith(b"\x1aE\xdf\xa3")
    assert len(result.sha256) == 64
