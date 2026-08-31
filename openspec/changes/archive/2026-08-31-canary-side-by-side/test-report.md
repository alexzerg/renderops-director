# Canary Side-by-Side Test Report

Version: 0.6.3
Score: 10/10
Critical issues: 0
Verdict: PASS

- Canary comparison: VP9, 1280×720, 8 seconds.
- Left label: FAILED V47.
- Right label: CANARY V46-SAFE.
- Shared frame range: 1042–1046.
- Verification label: 5/5 frames, VRAM 72%.
- Left/right SSIM at artifact moment: 0.573, proving a clear visual difference.
- Ruff passed; 27 tests passed; JavaScript syntax passed.
