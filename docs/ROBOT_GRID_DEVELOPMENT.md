# CEDARS EMPIRE Robot Development Foundation

## Current scope
This branch adds a vendor-neutral, simulation-oriented foundation for:
- Industrial Robotics
- Warehouse Robotics
- Agriculture Robotics
- Solar & Energy Robotics
- Robot Vision & Telemetry

All catalogue entries start in **standby**. The module does not connect to hardware, issue physical commands, store evidence files, connect to PostgreSQL, or move money.

## Safety and payment gates
- A robot may only be considered command-capable when its connection, hardware verification, and safety review flags are all true. Production command adapters must enforce this gate server-side.
- Task transitions are explicit and invalid transitions are rejected.
- Required evidence references must be present before evidence submission.
- Acceptance requires a named reviewer.
- Payment reconciliation requires an accepted task, transaction hash, and independently verified payment flag.
- The test suite uses placeholder evidence references and a fake transaction hash only to test workflow rules. These are not real evidence or a real payment.

## Planned integration sequence
1. Unit tests and static checks.
2. Add durable PostgreSQL tables/migrations for robot registry, robot status history, tasks, evidence metadata, reviewer decisions, and payment reconciliation records.
3. Add authentication and role-based permissions; provider/robot operators cannot approve their own evidence or reconcile their own payments.
4. Add a read-only telemetry adapter and simulated adapter before any live hardware adapter.
5. Add durable evidence upload/storage with content hashes, access controls, retention policy, and audit events.
6. Integrate with the existing Grid Marketplace navigation without replacing existing pages.
7. Add network-specific payment verification and duplicate transaction protection. No signing keys or custody functions belong in this module.
8. Run per-grid registration, task lifecycle, evidence, payment reconciliation, persistence, security, and regression tests.
9. Enable a grid only after its recorded checks pass and the owner approves deployment.

## Hardware requirements before physical deployment
Each robot type needs a documented model/firmware, vendor protocol, safe stop behavior, emergency stop validation, permitted operating envelope, operator permissions, maintenance process, and site acceptance test. Do not send commands to physical equipment based only on this software registry.
