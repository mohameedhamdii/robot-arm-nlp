"""Unit tests for Natural Language Task Planning."""
import pytest
from src.task_planner.task_planner_node import TaskPlanner


@pytest.fixture
def planner():
    return TaskPlanner()


def test_single_pick_and_place(planner):
    visible = ["red_block", "blue_block", "green_block", "red_mat", "blue_mat", "green_mat"]
    cmd = "pick up the red block and place it on the blue mat"
    plan = planner.generate_plan(cmd, visible)

    assert len(plan) == 2
    assert plan[0]["action"] == "pick"
    assert plan[0]["object_name"] == "red_block"
    assert plan[1]["action"] == "place"
    assert plan[1]["target_name"] == "blue_mat"


def test_compound_instruction(planner):
    visible = ["red_block", "blue_block", "green_block", "red_mat", "blue_mat", "green_mat"]
    cmd = "Put the red block on the blue mat and the green block on the red mat"
    plan = planner.generate_plan(cmd, visible)

    assert len(plan) == 4
    assert plan[0]["action"] == "pick"
    assert plan[0]["object_name"] == "red_block"
    assert plan[1]["action"] == "place"
    assert plan[1]["target_name"] == "blue_mat"
    assert plan[2]["action"] == "pick"
    assert plan[2]["object_name"] == "green_block"
    assert plan[3]["action"] == "place"
    assert plan[3]["target_name"] == "red_mat"


def test_transfer_phrasing(planner):
    visible = ["yellow_block", "green_mat"]
    cmd = "move the yellow block to the green mat"
    plan = planner.generate_plan(cmd, visible)

    assert len(plan) == 2
    assert plan[0]["action"] == "pick"
    assert plan[0]["object_name"] == "yellow_block"
    assert plan[1]["action"] == "place"
    assert plan[1]["target_name"] == "green_mat"


def test_empty_or_whitespace_input(planner):
    visible = ["red_block", "blue_mat"]
    plan = planner.generate_plan("   ", visible)
    assert plan == []
