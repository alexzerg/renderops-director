# Closed-Loop Recovery Requirements

Version: 0.6.0

After the live investigation, require explicit human approval for a five-frame canary. Emit canary telemetry to Grafana Cloud and verify Prometheus, Loki, and Tempo before unlocking the failed-frame recovery. Require a second approval, emit recovery telemetry, verify 38/38 frames, and display the editorial-ready recovered shot.
