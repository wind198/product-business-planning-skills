# Learning and simulation concepts — proposals, not SAD

## Curriculum
Stage 0 electricity, energy, motion and signals (simple circuit); stage 1 voltage/current/resistance, analog/digital, instruments (adjustable lighting); stage 2 C/C++, GPIO, loops, timers/state machines (pedestrian crossing); stage 3 ESP32 sensors, actuators, protocols, interrupts, connectivity (greenhouse); stage 4 coordinate systems, kinematics, motors, encoders, odometry and PID (mobile robot); stage 5 ROS2, navigation, perception, integration and reliability (warehouse transportation). Teach math/physics in context.

## Learning and assessment
Predict, experiment, assemble, implement, debug, optimize, design, handle faults, integrate and build open-ended projects. Projects carry requirements, constraints, components, milestones, acceptance criteria and rubric. Replay failure, inspect signals, provide progressive hints. Example gate assignment: closed when empty, open for arrival, close after departure, stop closing on obstruction, safe state when sensor fails. This is an illustrative simulated lesson, not a physical safety specification.

## Technical candidates
Education domain: curriculum, competency, assignments, assessment, tutor, projects. Simulation orchestrator: scenario, clock, telemetry and runtime lifecycle. Replaceable concept/circuit/MCU/physics adapters. Candidate stack Next.js, React, SVG/Canvas/Three.js, CircuitJS/ngspice, Wokwi/QEMU, Monaco, ESP-IDF/PlatformIO, Rapier, Gazebo/Isaac Sim, ROS2, SimReady/OpenUSD/GLB, NestJS/PostgreSQL, Git-based MDX.

ESP32 firmware -> MCU emulator -> bridge (MQTT/WebSocket candidate) -> physics world -> virtual sensor feedback. Wokwi-to-SimReady integration is not verified; asset conversion to GLB does not preserve all physical semantics. Timing fidelity, licensing, browser embedding, safety and costs require investigation. Hardware-in-loop is a future possibility.

Curriculum as code: competency graph, learning paths, lesson MDX, objectives, playground config, examples, homework, scenarios, tests, hints and rubrics. CI verifies reference implementations. No stack selection approved.
