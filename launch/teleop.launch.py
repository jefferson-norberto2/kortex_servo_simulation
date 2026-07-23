import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder

def generate_launch_description():
    # 1. Use the MoveItConfigsBuilder to neatly load all robot descriptions and kinematics
    # This automatically runs xacro on the main URDF and loads SRDF, Kinematics, and Joint Limits
    moveit_config = (
        MoveItConfigsBuilder(
            robot_name="gen3_lite",
            package_name="kinova_gen3_lite_moveit_config"
        )
        .robot_description(file_path=os.path.join(
            get_package_share_directory("kortex_description"), 
            "robots", 
            "gen3_lite_gen3_lite_2f.xacro"
        ))
        .robot_description_semantic(file_path="config/gen3_lite.srdf")
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .joint_limits(file_path="config/joint_limits.yaml") # Crucial for servo smoothing
        .to_moveit_configs()
    )

    # 2. Load the servo configuration parameters
    servo_yaml_path = os.path.join(
        get_package_share_directory('kortex_teleop'),
        'config',
        'servo_config.yaml'
    )
    with open(servo_yaml_path, 'r') as file:
        servo_yaml = yaml.safe_load(file)
    
    # Wrap in moveit_servo namespace as required by the C++ node
    servo_params = {"moveit_servo": servo_yaml}

    # 3. Define the python teleop node
    twist_to_stamped_node = Node(
        package='kortex_teleop',
        executable='twist_to_stamped',
        name='twist_to_stamped',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    # 4. Define the Servo node, passing all configurations extracted by the builder
    servo_node = Node(
        package='moveit_servo',
        executable='servo_node',
        name='servo_node',
        parameters=[
            servo_params,
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
            {'use_sim_time': True}          
        ],
        output='screen'
    )

    return LaunchDescription([
        twist_to_stamped_node,
        servo_node
    ])