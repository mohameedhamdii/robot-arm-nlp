"""Integration tests for Orchestrator Pipeline."""
import pytest
from src.orchestrator.orchestrator_node import OrchestratorPipeline


@pytest.fixture
def orchestrator():
    # Force mock hardware for fast headless test execution
    return OrchestratorPipeline(force_mock_hardware=True)


def test_end_to_end_execution(orchestrator):
    cmd = "pick up the red block and place it on the blue mat"
    result = orchestrator.execute_instruction(cmd)

    assert result["status"] == "success"
    assert result["steps_total"] == 2
    assert result["steps_completed"] == 2
    assert len(result["errors"]) == 0
    assert result["duration_s"] > 0


def test_missing_object_fails_gracefully(orchestrator):
    cmd = "pick up the purple block and place it on the orange mat"
    result = orchestrator.execute_instruction(cmd)

    assert result["status"] == "failed"
    assert len(result["errors"]) > 0
    assert any("not found" in err.lower() or "could not generate" in err.lower() for err in result["errors"])
