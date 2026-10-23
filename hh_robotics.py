"""Safe, vendor-neutral robot grid foundation for CEDARS EMPIRE.

This module defines a simulation-only registry and task state machine. It does not
connect to hardware, issue robot commands, upload evidence, or move funds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class RobotStatus(str, Enum):
    STANDBY = "standby"
    REGISTERED = "registered"
    CONNECTED = "connected"
    MAINTENANCE = "maintenance"
    BLOCKED = "blocked"


class TaskStatus(str, Enum):
    REGISTERED = "registered"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    EVIDENCE_SUBMITTED = "evidence_submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PAYMENT_RECONCILED = "payment_reconciled"


ALLOWED_TRANSITIONS = {
    TaskStatus.REGISTERED: {TaskStatus.ASSIGNED},
    TaskStatus.ASSIGNED: {TaskStatus.IN_PROGRESS},
    TaskStatus.IN_PROGRESS: {TaskStatus.EVIDENCE_SUBMITTED},
    TaskStatus.EVIDENCE_SUBMITTED: {TaskStatus.ACCEPTED, TaskStatus.REJECTED},
    TaskStatus.ACCEPTED: {TaskStatus.PAYMENT_RECONCILED},
    TaskStatus.REJECTED: {TaskStatus.ASSIGNED},
    TaskStatus.PAYMENT_RECONCILED: set(),
}


@dataclass
class RobotRecord:
    name: str
    grid_id: str
    equipment_type: str
    provider_id: str
    robot_id: str = field(default_factory=lambda: f"robot_{uuid4().hex}")
    status: RobotStatus = RobotStatus.STANDBY
    hardware_verified: bool = False
    safety_reviewed: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def can_receive_commands(self) -> bool:
        """Fail closed: no commands until real hardware and safety checks exist."""
        return (
            self.status == RobotStatus.CONNECTED
            and self.hardware_verified
            and self.safety_reviewed
        )


@dataclass
class RobotTask:
    grid_id: str
    title: str
    required_evidence: tuple[str, ...]
    task_id: str = field(default_factory=lambda: f"task_{uuid4().hex}")
    status: TaskStatus = TaskStatus.REGISTERED
    robot_id: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    accepted_by: str | None = None
    payment_tx_hash: str | None = None
    payment_verified: bool = False
    audit_events: list[dict[str, str]] = field(default_factory=list)

    def transition(self, target: TaskStatus, actor: str) -> None:
        if target not in ALLOWED_TRANSITIONS[self.status]:
            raise ValueError(f"Invalid task transition: {self.status.value} -> {target.value}")
        if target == TaskStatus.EVIDENCE_SUBMITTED:
            missing = [kind for kind in self.required_evidence if kind not in self.evidence_refs]
            if missing:
                raise ValueError(f"Required evidence missing: {', '.join(missing)}")
        if target == TaskStatus.ACCEPTED:
            if not actor.strip():
                raise ValueError("An authenticated reviewer is required")
            self.accepted_by = actor
        if target == TaskStatus.PAYMENT_RECONCILED:
            if not self.payment_verified or not self.payment_tx_hash:
                raise ValueError("Payment cannot be reconciled without verified transaction evidence")
        self.status = target
        self.audit_events.append({
            "status": target.value,
            "actor": actor,
            "at": datetime.now(timezone.utc).isoformat(),
        })

    def add_evidence_reference(self, evidence_type: str, reference: str) -> None:
        if self.status != TaskStatus.IN_PROGRESS:
            raise ValueError("Evidence can only be submitted while task is in progress")
        if not evidence_type.strip() or not reference.strip():
            raise ValueError("Evidence type and durable reference are required")
        self.evidence_refs.append(evidence_type)

    def attach_verified_payment(self, tx_hash: str, verified: bool) -> None:
        if self.status != TaskStatus.ACCEPTED:
            raise ValueError("Payment reconciliation requires an accepted task")
        if not tx_hash.strip() or not verified:
            raise ValueError("A transaction hash and independent verification are required")
        self.payment_tx_hash = tx_hash
        self.payment_verified = True


def robot_grid_catalog() -> list[dict[str, str]]:
    """Catalog entries remain standby until real integration checks are recorded."""
    return [
        {"id": "industrial_robotics", "name": "Industrial Robotics", "status": "standby"},
        {"id": "warehouse_robotics", "name": "Warehouse Robotics", "status": "standby"},
        {"id": "agriculture_robotics", "name": "Agriculture Robotics", "status": "standby"},
        {"id": "solar_energy_robotics", "name": "Solar & Energy Robotics", "status": "standby"},
        {"id": "robot_vision_telemetry", "name": "Robot Vision & Telemetry", "status": "standby"},
    ]
