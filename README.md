# Kortex Servo Simulation for Kinova Gen3 Lite

This package provides a servo node interface for the Kinova Gen3 Lite robotic arm using ROS 2 Jazzy and MoveIt 2 Servo. It allows you to control the robot in simulation (and real hardware) using Twist commands in Gazebo.

## Overview

The Gen3 Lite simulated environment does not natively accept Twist commands out of the box. This package acts as a bridge by:
1. Converting `geometry_msgs/Twist` messages from standard teleop nodes into `geometry_msgs/TwistStamped` expected by MoveIt Servo.
2. Automatically calling the `switch_command_type` service to configure the Servo node for Cartesian Twist commands.
3. Sending an initial Joint Trajectory command to slightly bend the arm upon startup, preventing the robot from locking up in a singularity state (which occurs when the arm is fully extended at position 0).

## Prerequisites

This package requires ROS 2 Jazzy and the following dependencies:

* [ros_kortex](https://github.com/Kinovarobotics/ros_kortex) (Kinova's official ROS 2 repository)
* `moveit_servo`
* `teleop_twist_keyboard`

To install the required standard ROS 2 packages, you can run:

```bash
sudo apt update
sudo apt install ros-jazzy-moveit-servo ros-jazzy-teleop-twist-keyboard
```

## Installation

1. Navigate to the `src` directory of your ROS 2 workspace:
   ```bash
   cd ~/ros2_ws/src
   ```

2. Clone this repository:
   ```bash
   git clone [https://github.com/jefferson-norberto2/kortex_teleop.git](https://github.com/jefferson-norberto2/kortex_teleop.git)
   ```

3. Build the workspace:
   ```bash
   cd ~/ros2_ws
   colcon build --packages-select kortex_teleop
   ```

4. Source the setup file:
   ```bash
   source install/setup.bash
   ```

## Usage

You need two separate terminal windows to run the teleoperation.

**Terminal 1: Launch the Servo Node and Twist Converter**

This launch file starts the MoveIt Servo node and the custom `twist_to_stamped` node. It also automatically moves the robot out of the initial singularity.

```bash
ros2 launch kortex_teleop teleop.launch.py
```

*Note: Wait a few seconds for the initial trajectory to finish executing and for the terminal to display "Twist mode activated successfully!".*

**Terminal 2: Run the Keyboard Teleop**

Start the standard ROS 2 keyboard teleoperation node:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Use the keys defined by `teleop_twist_keyboard` (e.g., `u`, `i`, `o`, `j`, `k`, `l`, `m`, `,`, `.`) to move the robotic arm in Cartesian space.

## Node Description

### `twist_to_stamped`
* **Subscribes to:** `/cmd_vel` (`geometry_msgs/Twist`)
* **Publishes to:** 
  * `/servo_node/delta_twist_cmds` (`geometry_msgs/TwistStamped`)
  * `/joint_trajectory_controller/joint_trajectory` (`trajectory_msgs/JointTrajectory`) - *Only once at startup.*
* **Service Client:** `/servo_node/switch_command_type` (`moveit_msgs/srv/ServoCommandType`)

## Configuration

The MoveIt Servo parameters are defined in `config/servo_config.yaml`. It includes configurations for collision checking, command scaling, and singularity thresholds to prevent sudden stops when the arm approaches its kinematic limits.
