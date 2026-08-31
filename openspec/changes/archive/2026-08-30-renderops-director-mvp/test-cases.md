# Test Cases

Version: 0.1.0

## Scenario: health check
Given the service is running
When `/api/health` is requested
Then HTTP 200 reports the application version and active runtime modes.

## Scenario: deterministic demo incident
Given demo mode is enabled
When shot `SH-042` is investigated
Then the response contains render evidence, a root cause, recovery actions and an approval requirement.

## Scenario: live integration configuration
Given Grafana MCP transport is `remote` or `stdio`
When the ADK agent is built
Then an `McpToolset` is configured with only approved read tools.

## Scenario: browser workflow
Given the home page is open
When the operator starts the investigation
Then the page renders the incident brief without a navigation reload.
