import pytest
from google.adk.tools import FunctionTool

from app.agent import READ_ONLY_GRAFANA_TOOLS, build_tools


@pytest.mark.parametrize(
    "forbidden",
    ["update_dashboard", "create_incident", "add_activity_to_incident", "create_folder"],
)
def test_write_tools_are_not_exposed(forbidden: str) -> None:
    assert forbidden not in READ_ONLY_GRAFANA_TOOLS


def test_demo_transport_builds_function_tool() -> None:
    tools = build_tools("demo")
    assert len(tools) == 1
    assert isinstance(tools[0], FunctionTool)


def test_unknown_transport_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        build_tools("magic")
