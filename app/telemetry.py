"""Production-shaped synthetic render telemetry exported to Grafana Cloud OTLP."""

import base64
import logging
import os
import time
from typing import Any

from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.trace import Status, StatusCode

SCENARIOS: dict[str, dict[str, Any]] = {
    "failure": {
        "frames_total": 240,
        "frames_failed": 38,
        "gpu_memory": 96,
        "gpu_utilization": 17,
        "queue_delay": 23,
        "frame_duration": 92.4,
        "asset_version": "texture-package-v47",
        "frame": 1042,
    },
    "canary": {
        "frames_total": 5,
        "frames_failed": 0,
        "gpu_memory": 72,
        "gpu_utilization": 68,
        "queue_delay": 0,
        "frame_duration": 48.3,
        "asset_version": "texture-package-v46-safe",
        "frame": 1042,
    },
    "recovery": {
        "frames_total": 38,
        "frames_failed": 0,
        "gpu_memory": 74,
        "gpu_utilization": 66,
        "queue_delay": 0,
        "frame_duration": 51.2,
        "asset_version": "texture-package-v46-safe",
        "frame": 1042,
    },
}


def telemetry_enabled() -> bool:
    return os.environ.get("RENDEROPS_SEED_TELEMETRY", "false").lower() == "true"


def _otlp_config() -> tuple[str, dict[str, str]]:
    endpoint = os.environ.get("GRAFANA_OTLP_ENDPOINT", "").rstrip("/")
    instance_id = os.environ.get("GRAFANA_OTLP_INSTANCE_ID", "").strip()
    token = os.environ.get("GRAFANA_OTLP_TOKEN", "").strip()
    if not endpoint or not instance_id or not token:
        raise RuntimeError(
            "GRAFANA_OTLP_ENDPOINT, GRAFANA_OTLP_INSTANCE_ID, and GRAFANA_OTLP_TOKEN "
            "are required to seed telemetry"
        )
    encoded = base64.b64encode(f"{instance_id}:{token}".encode()).decode()
    return endpoint, {"Authorization": f"Basic {encoded}"}


def _scenario(phase: str) -> dict[str, Any]:
    if phase not in SCENARIOS:
        raise ValueError(f"Unsupported render telemetry phase: {phase}")
    return SCENARIOS[phase]


def _resource(shot_id: str, phase: str) -> Resource:
    return Resource.create(
        {
            "service.name": "render-worker",
            "service.namespace": "renderops",
            "deployment.environment": "hackathon-live",
            "render.sequence": "SQ12",
            "render.shot": shot_id,
            "render.phase": phase,
            "render.engine": "cinematic-renderer",
        }
    )


def _labels(shot_id: str, phase: str, data: dict[str, Any]) -> dict[str, str]:
    return {
        "shot_id": shot_id,
        "sequence": "SQ12",
        "render_pass": "denoise.final-pass",
        "asset_version": data["asset_version"],
        "renderer": "cinematic-renderer",
        "recovery_phase": phase,
    }


def _export_metrics(
    endpoint: str,
    headers: dict[str, str],
    shot_id: str,
    phase: str,
    execution: dict[str, int | str] | None = None,
) -> bool:
    data = _scenario(phase)
    exporter = OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics", headers=headers)
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=60_000)
    provider = MeterProvider(resource=_resource(shot_id, phase), metric_readers=[reader])
    meter = provider.get_meter("renderops.telemetry")
    labels = _labels(shot_id, phase, data)
    samples = {
        "render_frames_total": (data["frames_total"], "frames"),
        "render_frames_failed": (data["frames_failed"], "frames"),
        "render_gpu_memory_usage_percent": (data["gpu_memory"], "%"),
        "render_gpu_utilization_percent": (data["gpu_utilization"], "%"),
        "render_queue_delay_minutes": (data["queue_delay"], "min"),
        "render_frame_duration_seconds": (data["frame_duration"], "s"),
        "render_full_rerender_cost_usd": (186.4, "1"),
        "render_failed_frames_cost_usd": (31.7, "1"),
        "render_canary_cost_usd": (4.2, "1"),
    }
    if execution:
        samples.update(
            {
                "render_job_exit_code": (int(execution["exit_code"]), ""),
                "render_job_duration": (int(execution["duration_ms"]), "ms"),
                "render_job_output": (int(execution["output_bytes"]), "By"),
                "render_job_frames_processed": (
                    int(execution["frames_processed"]),
                    "frames",
                ),
            }
        )
    for name, (value, unit) in samples.items():
        meter.create_gauge(name, unit=unit).set(value, labels)
    result = provider.force_flush(timeout_millis=20_000)
    provider.shutdown()
    return result


def _export_logs(
    endpoint: str,
    headers: dict[str, str],
    shot_id: str,
    phase: str,
    execution: dict[str, int | str] | None = None,
) -> bool:
    data = _scenario(phase)
    exporter = OTLPLogExporter(endpoint=f"{endpoint}/v1/logs", headers=headers)
    provider = LoggerProvider(resource=_resource(shot_id, phase))
    provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=provider)
    logger = logging.getLogger(f"renderops.synthetic.renderer.{phase}")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    common = {
        **_labels(shot_id, phase, data),
        "worker_pool": "gpu-a10-west",
    }
    if execution:
        logger.info(
            "FFmpeg %s render completed with exit code %s in %s milliseconds",
            phase,
            execution["exit_code"],
            execution["duration_ms"],
            extra={**common, **execution},
        )
    if phase == "failure":
        logger.info("Render batch accepted: 240 frames for editorial review", extra=common)
        for frame in (1042, 1047, 1051, 1063):
            logger.error(
                "CUDA out of memory while allocating denoiser tile buffer for frame %s",
                frame,
                extra={**common, "frame": frame, "gpu_memory_percent": 96},
            )
        logger.warning(
            "Retry budget exhausted after asset update texture-package-v47",
            extra={**common, "failed_frames": 38, "retry_count": 8},
        )
    elif phase == "canary":
        logger.info(
            "Canary render completed: 5/5 frames passed final denoise",
            extra={**common, "frames_tested": 5, "failed_frames": 0},
        )
        logger.info(
            "GPU memory stabilized at 72 percent with safe asset configuration",
            extra={**common, "gpu_memory_percent": 72},
        )
    else:
        logger.info(
            "Recovery rerender completed: 38/38 frames restored",
            extra={**common, "frames_restored": 38, "failed_frames": 0},
        )
        logger.info(
            "Shot SH-042 marked editorial ready",
            extra={**common, "editorial_ready": True},
        )
    result = provider.force_flush(timeout_millis=20_000)
    provider.shutdown()
    return result


def _export_traces(
    endpoint: str,
    headers: dict[str, str],
    shot_id: str,
    phase: str,
    execution: dict[str, int | str] | None = None,
) -> bool:
    data = _scenario(phase)
    exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces", headers=headers)
    provider = TracerProvider(resource=_resource(shot_id, phase))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("renderops.telemetry")
    with tracer.start_as_current_span("render.shot") as shot_span:
        shot_span.set_attribute("shot.id", shot_id)
        shot_span.set_attribute("recovery.phase", phase)
        shot_span.set_attribute("render.frames.total", data["frames_total"])
        shot_span.set_attribute("render.frames.failed", data["frames_failed"])
        if execution:
            shot_span.set_attribute("render.executor", str(execution["executor"]))
            shot_span.set_attribute("render.exit_code", int(execution["exit_code"]))
            shot_span.set_attribute("render.actual_duration_ms", int(execution["duration_ms"]))
            shot_span.set_attribute("render.output_bytes", int(execution["output_bytes"]))
            shot_span.set_attribute("render.output_sha256", str(execution["sha256"]))
        with tracer.start_as_current_span("render.frame") as frame_span:
            frame_span.set_attribute("shot.id", shot_id)
            frame_span.set_attribute("recovery.phase", phase)
            frame_span.set_attribute("frame.number", data["frame"])
            frame_span.set_attribute("asset.version", data["asset_version"])
            with tracer.start_as_current_span("denoise.final-pass") as denoise_span:
                denoise_span.set_attribute("shot.id", shot_id)
                denoise_span.set_attribute("recovery.phase", phase)
                denoise_span.set_attribute("gpu.memory.percent", data["gpu_memory"])
                denoise_span.set_attribute("render.duration.seconds", data["frame_duration"])
                if phase == "failure":
                    denoise_span.set_attribute("retry.count", 8)
                    denoise_span.set_status(
                        Status(StatusCode.ERROR, "CUDA tile allocation failed")
                    )
                    denoise_span.add_event(
                        "cuda.out_of_memory",
                        {"requested_mb": 1920, "available_mb": 640},
                    )
                else:
                    denoise_span.set_attribute("retry.count", 0)
                    denoise_span.set_status(Status(StatusCode.OK))
                    denoise_span.add_event(
                        f"{phase}.validated",
                        {"frames_failed": 0, "gpu_memory_percent": data["gpu_memory"]},
                    )
        if phase == "failure":
            shot_span.set_status(Status(StatusCode.ERROR, "38 frames failed"))
        else:
            shot_span.set_status(Status(StatusCode.OK))
    result = provider.force_flush(timeout_millis=20_000)
    provider.shutdown()
    return result


def seed_render_telemetry(
    shot_id: str,
    phase: str = "failure",
    execution: dict[str, int | str] | None = None,
) -> dict[str, object]:
    """Export render evidence and optional real execution metadata."""
    normalized = shot_id.strip().upper()
    _scenario(phase)
    endpoint, headers = _otlp_config()
    started = time.monotonic()
    metrics_ok = _export_metrics(endpoint, headers, normalized, phase, execution)
    logs_ok = _export_logs(endpoint, headers, normalized, phase, execution)
    traces_ok = _export_traces(endpoint, headers, normalized, phase, execution)
    return {
        "shot_id": normalized,
        "phase": phase,
        "metrics": metrics_ok,
        "logs": logs_ok,
        "traces": traces_ok,
        "duration_ms": round((time.monotonic() - started) * 1000),
    }
