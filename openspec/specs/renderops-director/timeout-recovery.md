# Agent Timeout Recovery Pattern

Version: 0.3.1

Run a bounded deterministic MCP collector in parallel with an exploratory tool-using agent. If the agent returns a valid structured result, cancel the collector. If the agent times out, errors, or omits a final event, normalize the already collected MCP evidence through a schema-constrained model call. Retain a final evidence-only response so UI contracts never collapse to empty state.
