from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    use_voice_arg = DeclareLaunchArgument(
        'use_voice' ,
        default_value='false',
        description='Enable voice capture input mode instead of terminal text'
    )

    use_yolo_arg =DeclareLaunchArgument(
        'use_yolo',
        default_value = 'false',
        description = 'Enable YOLOv8 neural object detection instead of color segmentation'
    )

    perception_node= Node(
        package='robot_arm_nlp',
        executable = 'perception',
        name = 'perception_node',
        output='screen',
        parameters =[{'use_yolo': LaunchConfiguration ('use_yolo')}]
    )

    task_planner_node=Node (
        package='robot_arm_nlp',
        executable='task_planner',
        name='task_planner_node',
        output='screen'
    )



    motion_node =Node(
        package='robot_arm_nlp',
        executable='motion',
        name = 'motion_node' ,
        output = 'screen'
    )

    orchestrator_node= Node(
        package = 'robot_arm_nlp',
        executable='orchestrator' ,
        name='orchestrator_node',
        output='screen'
    )

    input_handler_node=Node (
        package='robot_arm_nlp',
        executable= 'input_handler' ,
        name='input_handler_node',
        output='screen',
        parameters=[{'use_voice':LaunchConfiguration( 'use_voice') }]
    )

    return LaunchDescription([
        use_voice_arg,
        use_yolo_arg,
        perception_node,
        task_planner_node,
        motion_node,
        orchestrator_node,
        input_handler_node
    ])
