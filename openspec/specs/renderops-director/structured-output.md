# Structured Tool-Agent Output Pattern

Version: 0.2.3

Do not couple tool orchestration reliability to final response formatting. Let the primary ADK agent investigate with MCP. Capture bounded function responses. Accept a valid first-pass JSON payload when available; otherwise run a separate schema-constrained Gemini call over those responses. The normalizer may summarize but must not invent evidence absent from the tool results.
