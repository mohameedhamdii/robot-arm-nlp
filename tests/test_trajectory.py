"""Unit tests for Trajectory Generation."""
import pytest
from src.motion.ik_solver import JointAngles
from src.motion.trajectory import TrajectoryGenerator


def test_trajectory_endpoints():
    gen = TrajectoryGenerator(step_delay_s=0.05)
    start = JointAngles(90.0, 90.0, 90.0, 90.0, 90.0, 30.0)
    goal = JointAngles(45.0, 60.0, 120.0, 80.0, 90.0, 110.0)

    traj = gen.interpolate(start, goal, duration_s=1.0)
    assert len(traj) > 0

    first_pt = traj[0]
    last_pt = traj[-1]

    assert first_pt.time_s == 0.0
    assert first_pt.angles.base_yaw == 90.0
    assert last_pt.angles.base_yaw == 45.0
    assert last_pt.angles.gripper == 110.0


def test_monotonic_time_progression():
    gen = TrajectoryGenerator(step_delay_s=0.05)
    start = JointAngles(90.0, 90.0, 90.0, 90.0, 90.0, 30.0)
    goal = JointAngles(100.0, 80.0, 90.0, 90.0, 90.0, 30.0)

    traj = gen.interpolate(start, goal, duration_s=0.5)
    for i in range(1, len(traj)):
        assert traj[i].time_s > traj[i - 1].time_s
