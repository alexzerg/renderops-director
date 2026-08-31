"""Small real FFmpeg render executor for the approval-gated demo workflow."""

import base64
import hashlib
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

MEDIA_DIR = Path(__file__).resolve().parent / "static" / "media"


@dataclass(frozen=True)
class RenderArtifact:
    phase: str
    exit_code: int
    duration_ms: int
    frames_processed: int
    output_bytes: int
    sha256: str
    media_mime: str
    media_base64: str

    def telemetry(self) -> dict[str, int | str]:
        return {
            "executor": "ffmpeg",
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "frames_processed": self.frames_processed,
            "output_bytes": self.output_bytes,
            "sha256": self.sha256,
        }


def _canary_command(output: Path) -> list[str]:
    failed = MEDIA_DIR / "shot-sh042-failed.mp4"
    source = MEDIA_DIR / "shot-sh042-source.mp4"
    graph = (
        "[0:v]trim=start=1.20:end=1.38,setpts=24*(PTS-STARTPTS),"
        "scale=320:180[left];"
        "[1:v]trim=start=1.20:end=1.38,setpts=24*(PTS-STARTPTS),"
        "eq=contrast=1.04:saturation=1.06,scale=320:180[right];"
        "[left][right]hstack=inputs=2,pad=640:360:0:90:0x080b12,format=yuv420p[out]"
    )
    return [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(failed),
        "-i",
        str(source),
        "-filter_complex",
        graph,
        "-map",
        "[out]",
        "-r",
        "30",
        "-c:v",
        "libvpx-vp9",
        "-b:v",
        "0",
        "-crf",
        "34",
        "-an",
        str(output),
    ]


def _recovery_command(output: Path) -> list[str]:
    source = MEDIA_DIR / "shot-sh042-source.mp4"
    return [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-vf",
        "scale=640:360,eq=contrast=1.04:saturation=1.06,unsharp=5:5:0.55:3:3:0.2",
        "-t",
        "8",
        "-c:v",
        "libvpx-vp9",
        "-b:v",
        "0",
        "-crf",
        "34",
        "-an",
        str(output),
    ]


def execute_render_fix(phase: str) -> RenderArtifact:
    if phase not in {"canary", "recovery"}:
        raise ValueError(f"Unsupported FFmpeg render phase: {phase}")
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is not installed in the render runtime")
    frames = 5 if phase == "canary" else 38
    with tempfile.TemporaryDirectory(prefix=f"renderops-{phase}-") as tmp:
        output = Path(tmp) / f"shot-sh042-{phase}.webm"
        command = _canary_command(output) if phase == "canary" else _recovery_command(output)
        started = time.monotonic()
        process = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
        duration_ms = round((time.monotonic() - started) * 1000)
        if process.returncode != 0 or not output.exists():
            error = process.stderr.strip()[-1000:]
            raise RuntimeError(f"FFmpeg {phase} render failed: {error}")
        content = output.read_bytes()
    return RenderArtifact(
        phase=phase,
        exit_code=process.returncode,
        duration_ms=duration_ms,
        frames_processed=frames,
        output_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        media_mime="video/webm",
        media_base64=base64.b64encode(content).decode(),
    )
