"""
A ROS 2 node for controlling a robot arm using MoveIt Servo via keyboard input.

This script captures keyboard inputs in raw mode to provide real-time, non-blocking 
teleoperation of the robot's end-effector in Cartesian space (Y and Z axes). It runs 
the ROS 2 executor in a separate thread to ensure smooth control and publishing rates.
"""

import sys
import select
import termios
import tty
import threading

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from geometry_msgs.msg import TwistStamped
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
from moveit_msgs.srv import ServoCommandType


class KeyboardServoExample(Node):
    """
    A ROS 2 node that manages keyboard teleoperation for MoveIt Servo.
    
    Attributes:
        trajectory_pub (Publisher): Publishes the initial joint trajectory to escape singularities.
        publisher_ (Publisher): Publishes twist commands to MoveIt Servo.
        cli (Client): Service client to switch the MoveIt Servo command type.
        frame_id (str): The reference frame for the twist commands.
        startup_timer (Timer): Triggers the startup sequence once after initialization.
        startup_completed (bool): Flag indicating if the startup sequence is finished.
        speed (float): Current translation speed in meters per second.
        target_y (float): Target velocity along the Y-axis.
        target_z (float): Target velocity along the Z-axis.
        publish_timer (Timer): Continuously publishes the twist commands at a fixed rate.
    """

    def __init__(self):
        """Initializes the node, publishers, clients, timers, and state variables."""
        super().__init__('keyboard_servo_example')
        
        # Publisher for the initial trajectory command
        self.trajectory_pub = self.create_publisher(
            JointTrajectory,
            '/joint_trajectory_controller/joint_trajectory',
            10
        )
        
        # Direct publisher for MoveIt Servo
        self.publisher_ = self.create_publisher(
            TwistStamped,
            '/servo_node/delta_twist_cmds',
            10
        )
        
        self.cli = self.create_client(ServoCommandType, '/servo_node/switch_command_type')
        self.frame_id = 'base_link' 
        
        self.startup_timer = self.create_timer(1.0, self.startup_sequence)
        self.startup_completed = False

        # --- Teleop State Variables ---
        self.speed = 0.05
        self.target_y = 0.0
        self.target_z = 0.0
        
        # Timer to keep MoveIt Servo continuously updated (20 Hz)
        self.publish_timer = self.create_timer(0.05, self.publish_twist_callback)

    def startup_sequence(self):
        """
        Executes the initial setup steps for the robot.
        
        This moves the robot out of possible starting singularities and 
        switches MoveIt Servo to accept Twist commands.
        """
        if not self.startup_completed:
            self.move_out_of_singularity()
            self.activate_twist_mode()
            self.startup_completed = True
            self.startup_timer.cancel()

    def move_out_of_singularity(self):
        """
        Sends a predefined joint trajectory to move the robot arm slightly.
        
        This ensures the robot is not in a kinematic singularity before 
        Cartesian teleoperation begins.
        """
        self.get_logger().info('Sending initial trajectory to escape singularities...\r\n')
        
        msg = JointTrajectory()
        msg.joint_names = ['joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5', 'joint_6']
        
        point = JointTrajectoryPoint()
        point.positions = [0.1, 0.1, 1.5, 0.01, 0.5, 0.01] 
        
        duration = Duration()
        duration.sec = 3
        duration.nanosec = 0
        point.time_from_start = duration
        
        msg.points = [point]
        self.trajectory_pub.publish(msg)

    def activate_twist_mode(self):
        """
        Calls the MoveIt Servo service to switch the command input type to TWIST.
        """
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for Servo switch_command_type service...\r\n')
        
        req = ServoCommandType.Request()
        req.command_type = ServoCommandType.Request.TWIST 
        
        future = self.cli.call_async(req)
        future.add_done_callback(self.service_callback)
        
    def service_callback(self, future):
        """
        Callback triggered when the command type switch service responds.
        
        Args:
            future (rclpy.task.Future): The future object containing the service response.
        """
        try:
            response = future.result()
            self.get_logger().info(f'Twist mode activated successfully! Success: {response.success}\r\n')
        except Exception as e:
            self.get_logger().error(f'Failed to activate Twist mode: {e}\r\n')

    def publish_twist_callback(self):
        """
        Publishes the current target velocities to the Servo node continuously.
        
        This method is triggered by a timer and runs at 20 Hz to prevent 
        MoveIt Servo from halting due to command timeouts.
        """
        if not self.startup_completed:
            return
            
        stamped_msg = TwistStamped()
        stamped_msg.header.stamp = self.get_clock().now().to_msg()
        stamped_msg.header.frame_id = self.frame_id
        
        stamped_msg.twist.linear.y = self.target_y
        stamped_msg.twist.linear.z = self.target_z
        
        self.publisher_.publish(stamped_msg)

    def keyboard_loop(self):
        """
        Main blocking loop that captures keyboard input directly from the Linux terminal.
        
        Sets the terminal to raw mode to detect key holds and releases without requiring 
        the user to press the Enter key. Maps specific keys to movement and speed adjustments.
        """
        msg = """
Simplified control activated!
---------------------------
Movement (Hold down):
   w: +Z (Up)
   s: -Z (Down)
   a: -Y (Left)
   d: +Y (Right)
   
Speed:
   q: Increase speed (x1.1)
   e: Decrease speed (x0.9)
   
Press Ctrl+C to exit.
---------------------------
"""
        print(msg)
        settings = termios.tcgetattr(sys.stdin)
        
        try:
            tty.setraw(sys.stdin.fileno())
            while rclpy.ok():
                # Wait 100ms for a key press. If none, assume the user released the key.
                rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
                
                if rlist:
                    key = sys.stdin.read(1)
                else:
                    key = ''
                
                # Ctrl+C interrupt
                if key == '\x03': 
                    break
                
                # Simplified control logic
                if key == 'w':
                    self.target_z = self.speed
                    self.target_y = 0.0
                elif key == 's':
                    self.target_z = -self.speed
                    self.target_y = 0.0
                elif key == 'a':
                    self.target_y = self.speed
                    self.target_z = 0.0
                elif key == 'd':
                    self.target_y = -self.speed
                    self.target_z = 0.0
                elif key == 'q':
                    self.speed *= 1.1
                    # In raw mode, we must use \r to align and ANSI escape \033[K to clear line clutter
                    sys.stdout.write(f"\rCurrent speed: {self.speed:.4f} m/s \033[K")
                    sys.stdout.flush()
                elif key == 'e':
                    self.speed *= 0.9
                    self.speed = max(0.001, self.speed) # Prevent negative or absolute zero speed
                    sys.stdout.write(f"\rCurrent speed: {self.speed:.4f} m/s \033[K")
                    sys.stdout.flush()
                else:
                    # If no mapped key is held down, stop the robot
                    self.target_y = 0.0
                    self.target_z = 0.0

        finally:
            # Restore normal terminal settings upon exiting
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)


def main(args=None):
    """
    Entry point for the ROS 2 node.
    
    Initializes rclpy, sets up a multi-threaded executor to run ROS callbacks 
    in the background, and starts the blocking keyboard capture loop in the main thread.
    """
    rclpy.init(args=args)
    node = KeyboardServoExample()
    
    # Create an executor in a separate thread so that timers and subscriptions
    # work while the terminal loop "locks" the main thread.
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    
    try:
        # Start capturing keystrokes in the main thread
        node.keyboard_loop()
    except KeyboardInterrupt:
        pass
    finally:
        # When the loop finishes (Ctrl+C), clean up and shut down
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()