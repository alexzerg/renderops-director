"""Production-shaped synthetic render telemetry exported to Grafana Cloud OTLP."""

import base64
import logging
import os
import time

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


def _resource(shot_id: str) -> Resource:
    return Resource.create(
        {
            "service.name": "render-worker",
            "service.namespace": "renderops",
            "deployment.environment": "hackathon-live",
            "render.sequence": "SQ12",
            "render.shot": shot_id,
            "render.engine": "cinematic-renderer",
        }
    )


def _export_metrics(endpoint: str, headers: dict[str, str], shot_id: str) -> bool:
    exporter = OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics", headers=headers)
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=60_000)
    provider = MeterProvider(resource=_resource(shot_id), metric_readers=[reader])
    meter = provider.get_meter("renderops.telemetry")
    labels = {
        "shot_id": shot_id,
        "sequence": "SQ12",
        "render_pass": "denoise.final-pass",
        "asset_version": "texture-package-v47",
        "renderer": "cinematic-renderer",
    }
    samples = {
        "render_frames_total": (240, "frames"),
        "render_frames_failed": (38, "frames"),
        "render_gpu_memory_usage_percent": (96, "%"),
        "render_gpu_utilization_percent": (17, "%"),
        "render_queue_delay_minutes": (23, "min"),
        "render_frame_duration_seconds": (92.4, "s"),
        "render_full_rerender_cost_usd": (186.4, "1"),
        "render_failed_frames_cost_usd": (31.7, "1"),
        "render_canary_cost_usd": (4.2, "1"),
    }
    for name, (value, unit) in samples.items():
        meter.create_gauge(name, unit=unit).set(value, labels)
    result = provider.force_flush(timeout_millis=20_000)
    provider.shutdown()
    return result


def _export_logs(endpoint: str, headers: dict[str, str], shot_id: str) -> bool:
    exporter = OTLPLogExporter(endpoint=f"{endpoint}/v1/logs", headers=headers)
    provider = LoggerProvider(resource=_resource(shot_id))
    provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=provider)
    logger = logging.getLogger("renderops.synthetic.renderer")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    common = {
        "shot_id": shot_id,
        "sequence": "SQ12",
        "render_pass": "denoise.final-pass",
        "asset_version": "texture-package-v47",
        "worker_pool": "gpu-a10-west",
    }
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
    result = provider.force_flush(timeout_millis=20_000)
    provider.shutdown()
    return result


def _export_traces(endpoint: str, headers: dict[str, str], shot_id: str) -> bool:
    exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces", headers=headers)
    provider = TracerProvider(resource=_resource(shot_id))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("renderops.telemetry")
    with tracer.start_as_current_span("render.shot") as shot_span:
        shot_span.set_attribute("shot.id", shot_id)
        shot_span.set_attribute("render.frames.total", 240)
        shot_span.set_attribute("render.frames.failed", 38)
        with tracer.start_as_current_span("render.frame") as frame_span:
            frame_span.set_attribute("shot.id", shot_id)
            frame_span.set_attribute("frame.number", 1042)
            frame_span.set_attribute("asset.version", "texture-package-v47")
            with tracer.start_as_current_span("denoise.final-pass") as denoise_span:
                denoise_span.set_attribute("shot.id", shot_id)
                denoise_span.set_attribute("gpu.memory.percent", 96)
                denoise_span.set_attribute("retry.count", 8)
                denoise_span.set_attribute("render.duration.seconds", 92.4)
                denoise_span.set_status(Status(StatusCode.ERROR, "CUDA tile allocation failed"))
                denoise_span.add_event(
                    "cuda.out_of_memory",
                    {"requested_mb": 1920, "available_mb": 640},
                )
        shot_span.set_status(Status(StatusCode.ERROR, "38 frames failed"))
    result = provider.force_flush(timeout_millis=20_000)
    provider.shutdown()
    return result


def seed_render_telemetry(shot_id: str) -> dict[str, object]:
    """Export a bounded evidence set and return only non-sensitive delivery metadata."""
    normalized = shot_id.strip().upper()
    endpoint, headers = _otlp_config()
    started = time.monotonic()
    metrics_ok = _export_metrics(endpoint, headers, normalized)
    logs_ok = _export_logs(endpoint, headers, normalized)
    traces_ok = _export_traces(endpoint, headers, normalized)
    return {
        "shot_id": normalized,
        "metrics": metrics_ok,
        "logs": logs_ok,
        "traces": traces_ok,
        "duration_ms": round((time.monotonic() - started) * 1000),
    }
