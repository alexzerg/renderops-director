# Tangible Shot Preview Test Report

Version: 0.5.0
Score: 10/10
Critical issues: 0
Verdict: PASS

- Three WebM/VP9 previews: source, failed, canary.
- Three MP4/H.264 fallbacks.
- Every video: 1280×720, 30 fps, 8 seconds.
- Failed/source SSIM: 0.881, proving visible degradation.
- Canary/source SSIM: 0.965, proving visual recovery.
- Browser switched all three modes and loaded video metadata.
- Frame timeline: eight representative frames, four visibly failed.
- Result action switched the viewer to CANARY PASS.
- External media URLs: zero.
- Ruff passed; 24 tests passed; JavaScript syntax passed.
