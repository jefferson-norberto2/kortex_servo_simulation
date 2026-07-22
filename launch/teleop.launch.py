import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    config_file = os.path.join(
        get_package_share_directory('kortex_teleop'),
        'config',
        'servo_config.yaml'
    )

    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [FindPackageShare("kortex_description"), "robots", "gen3_lite_gen3_lite_2f.xacro"]
            ),
        ]
    )
    robot_description = {"robot_description": ParameterValue(robot_description_content, value_type=str)}

    robot_description_semantic_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [
                    FindPackageShare("kinova_gen3_lite_moveit_config"),
                    "config",
                    "gen3_lite.srdf"
                ]
            ),
        ]
    )
    robot_description_semantic = {"robot_description_semantic": ParameterValue(robot_description_semantic_content, value_type=str)}
    
    kinematics_yaml_path = os.path.join(
        get_package_share_directory('kinova_gen3_lite_moveit_config'),
        'config',
        'kinematics.yaml'
    )
    
    with open(kinematics_yaml_path, 'r') as file:
        kinematics_yaml = yaml.safe_load(file)
        
    robot_description_kinematics = {"robot_description_kinematics": kinematics_yaml}

    twist_to_stamped_node = Node(
        package='kortex_teleop',
        executable='twist_to_stamped',
        name='twist_to_stamped',
        output='screen',
        parameters=[{'use_sim_time': True}], # <--- Relógio da simulação ativado aqui
    )

    servo_node = Node(
        package='moveit_servo',
        executable='servo_node',
        name='servo_node',
        parameters=[
            config_file,
            robot_description,
            robot_description_semantic,
            robot_description_kinematics,
            {'use_sim_time': True}          # <--- Relógio da simulação ativado aqui
        ],
        output='screen'
    )

    return LaunchDescription([
        twist_to_stamped_node,
        servo_node
    ])