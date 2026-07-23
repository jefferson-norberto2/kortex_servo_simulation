import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TwistStamped
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
from moveit_msgs.srv import ServoCommandType

class TwistToTwistStamped(Node):
    def __init__(self):
        super().__init__('twist_to_stamped')
        
        # Publisher to send the initial trajectory command
        self.trajectory_pub = self.create_publisher(
            JointTrajectory,
            '/joint_trajectory_controller/joint_trajectory',
            10
        )
        
        self.publisher_ = self.create_publisher(
            TwistStamped,
            '/servo_node/delta_twist_cmds',
            10
        )
        
        self.cli = self.create_client(ServoCommandType, '/servo_node/switch_command_type')
        self.frame_id = 'base_link' 
        
        self.startup_timer = self.create_timer(1.0, self.startup_sequence)
        self.startup_completed = False

        self.subscription = self.create_subscription(
            Twist,
            'cmd_vel',
            self.listener_callback,
            10
        )

    def startup_sequence(self):
        if not self.startup_completed:
            self.move_out_of_singularity()
            self.activate_twist_mode()
            self.startup_completed = True
            self.startup_timer.cancel()

    def move_out_of_singularity(self):
        self.get_logger().info('Sending initial trajectory to escape singularity...')
        
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
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for Servo switch_command_type service...')
        
        req = ServoCommandType.Request()
        req.command_type = ServoCommandType.Request.TWIST 
        
        future = self.cli.call_async(req)
        future.add_done_callback(self.service_callback)
        
    def service_callback(self, future):
        try:
            response = future.result()
            self.get_logger().info(f'Twist mode activated successfully! Response: {response.success}')
        except Exception as e:
            self.get_logger().error(f'Failed to activate Twist mode: {e}')

    def listener_callback(self, msg: Twist):
        stamped_msg = TwistStamped()
        stamped_msg.header.stamp = self.get_clock().now().to_msg()
        stamped_msg.header.frame_id = self.frame_id
        stamped_msg.twist = msg
        self.publisher_.publish(stamped_msg)

def main(args=None):
    rclpy.init(args=args)
    node = TwistToTwistStamped()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()