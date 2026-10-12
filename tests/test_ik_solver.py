"""Unit tests for Inverse and Forward Kinematics."""
import pytest
import math
from src.motion.ik_solver import IKSolver, JointAngles, WorkspaceLimitError


@pytest.fixture
def solver():
    return IKSolver()


def test_workspace_boundary_enforcement(solver):
    """Asserts that targets outside safety box are rejected."""
    # X out of bounds
    with pytest.raises(WorkspaceLimitError):
        solver.solve_ik(250.0, 150.0, 50.0)

    with pytest.raises(WorkspaceLimitError):
        solver.solve_ik(-250.0, 150.0, 50.0)

    # Y out of bounds
    with pytest.raises(WorkspaceLimitError):
        solver.solve_ik(0.0, 10.0, 50.0)

    with pytest.raises(WorkspaceLimitError):
        solver.solve_ik(0.0, 350.0, 50.0)

    # Z out of bounds
    with pytest.raises(WorkspaceLimitError):
        solver.solve_ik(0.0, 150.0, -20.0)


def test_unreachable_point_rejection(solver):
    """Asserts that points beyond maximum link extension raise reachability errors."""
    with pytest.raises(WorkspaceLimitError):
        solver.solve_ik(150.0, 250.0, 190.0)


def test_joint_angle_limits(solver):
    """Asserts that solved angles always respect [0, 180] physical servo limits."""
    test_points = [
        (0.0, 120.0, 80.0),
        (-60.0, 130.0, 20.0),
        (50.0, 140.0, 40.0),
        (0.0, 150.0, 15.0),
    ]
    for x, y, z in test_points:
        angles = solver.solve_ik(x, y, z)
        for val in angles.to_list():
            assert 0.0 <= val <= 180.0, f"Angle {val} out of servo range [0, 180]"


def test_forward_inverse_consistency(solver):
    """Asserts that FK of solved IK produces coordinates within reasonable kinematic tolerance."""
    test_points = [
        (0.0, 130.0, 50.0),
        (-40.0, 140.0, 30.0),
        (40.0, 130.0, 40.0)
    ]
    for target_x, target_y, target_z in test_points:
        angles = solver.solve_ik(target_x, target_y, target_z, pitch_deg=-90.0)
        fk_x, fk_y, fk_z = solver.solve_fk(angles)
        
        # Base rotation accuracy
        assert math.isclose(fk_x, target_x, abs_tol=5.0), f"X mismatch: expected {target_x}, got {fk_x}"
        assert math.isclose(fk_y, target_y, abs_tol=5.0), f"Y mismatch: expected {target_y}, got {fk_y}"
        assert math.isclose(fk_z, target_z, abs_tol=8.0), f"Z mismatch: expected {target_z}, got {fk_z}"
