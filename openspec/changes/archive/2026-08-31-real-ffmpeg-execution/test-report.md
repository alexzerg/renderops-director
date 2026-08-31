# Real FFmpeg Execution Test Report

Version: 0.7.0
Score: 10/10
Critical issues: 0
Verdict: PASS

- Local canary FFmpeg: exit 0, five targeted frames, approximately 1 second, 36KB WebM.
- Local recovery FFmpeg: exit 0, 38 targeted frames, approximately 4 seconds, 147KB WebM.
- Container canary: exit 0 in 4032ms, 36854 bytes, unique SHA-256.
- Container recovery: exit 0 in 10542ms, 147121 bytes, unique SHA-256.
- Prometheus read-back includes job exit code, duration, frame count, and output bytes.
- Loki contains real FFmpeg completion logs.
- Tempo contains execution attributes and output SHA-256.
- Browser canary and recovery sources are generated `blob:` URLs.
- Ruff passed; 28 tests passed; JavaScript syntax passed; Docker build passed.
