# Grafana Evidence Map

| Production question | Grafana signal | MCP tool | Demonstrated evidence |
| --- | --- | --- | --- |
| How many frames failed? | Prometheus metric | `query_prometheus` | `render_frames_failed = 38` |
| Is the farm capacity-bound? | GPU utilization and memory | `query_prometheus` | 17% utilization, 96% memory |
| What failed in the renderer? | Structured Loki log | `query_loki_logs` | CUDA OOM in `denoise.final-pass` |
| Where is the critical path? | Tempo span and event | `tempo_traceql-search` | failed denoiser span with eight retries |
| What are the recovery economics? | Cost metrics | `query_prometheus` | full rerender vs failed frames vs canary |
| Can automation mutate production? | MCP startup and allowlist | runtime policy | `--disable-write`, human gate required |
