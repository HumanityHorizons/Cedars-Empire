import pytest

from hh_robotics import (
    RobotRecord, RobotStatus, RobotTask, TaskStatus, robot_grid_catalog,
)


def test_robot_grids_start_in_standby():
    catalog = robot_grid_catalog()
    assert len(catalog) >= 5
    assert all(item["status"] == "standby" for item in catalog)


def test_robot_commands_fail_closed_until_hardware_and_safety_verified():
    robot = RobotRecord("Test arm", "industrial_robotics", "arm", "provider-1")
    assert robot.status == RobotStatus.STANDBY
    assert not robot.can_receive_commands()
    robot.status = RobotStatus.CONNECTED
    assert not robot.can_receive_commands()
    robot.hardware_verified = True
    assert not robot.can_receive_commands()
    robot.safety_reviewed = True
    assert robot.can_receive_commands()


def test_task_requires_evidence_before_submission_and_payment_before_reconcile():
    task = RobotTask("warehouse_robotics", "Move pallet", ("photo", "telemetry"))
    task.transition(TaskStatus.ASSIGNED, "dispatcher")
    task.transition(TaskStatus.IN_PROGRESS, "robot-adapter")
    with pytest.raises(ValueError, match="Required evidence missing"):
        task.transition(TaskStatus.EVIDENCE_SUBMITTED, "provider")
    task.add_evidence_reference("photo", "evidence://test/photo-1")
    task.add_evidence_reference("telemetry", "evidence://test/telemetry-1")
    task.transition(TaskStatus.EVIDENCE_SUBMITTED, "provider")
    assert "evidence://test/photo-1" in task.evidence_refs
    assert "evidence://test/telemetry-1" in task.evidence_refs
    task.transition(TaskStatus.ACCEPTED, "reviewer-1")
    with pytest.raises(ValueError, match="transaction hash"):
        task.transition(TaskStatus.PAYMENT_RECONCILED, "finance-admin")
    task.attach_verified_payment("0x" + "a" * 64, verified=True)
    task.transition(TaskStatus.PAYMENT_RECONCILED, "finance-admin")
    assert task.status == TaskStatus.PAYMENT_RECONCILED


def test_invalid_transition_is_rejected():
    task = RobotTask("industrial_robotics", "Inspect machine", ("photo",))
    with pytest.raises(ValueError, match="Invalid task transition"):
        task.transition(TaskStatus.PAYMENT_RECONCILED, "finance-admin")


def test_evidence_only_accepted_during_in_progress():
    task = RobotTask("agriculture_robotics", "Inspect crop", ("image",))
    with pytest.raises(ValueError, match="only be submitted"):
        task.add_evidence_reference("image", "evidence://crop/1")


def test_duplicate_evidence_type_is_rejected():
    task = RobotTask("warehouse_robotics", "Count inventory", ("photo",))
    task.transition(TaskStatus.ASSIGNED, "dispatcher")
    task.transition(TaskStatus.IN_PROGRESS, "operator")
    task.add_evidence_reference("photo", "evidence://inventory/1")
    with pytest.raises(ValueError, match="Duplicate evidence type"):
        task.add_evidence_reference("photo", "evidence://inventory/2")
