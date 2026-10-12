import sys
import json
import logging
from typing import List, Dict, Any, Optional
try:
    from .llm_backend import LLMBackend
except(ImportError,ValueError) :
    from llm_backend import LLMBackend

logger= logging.getLogger("task_planner")

try:


    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String
    try:

        from robot_arm_nlp.msg import ActionStep, ActionList
        from robot_arm_nlp.srv import GetObjects
    except ImportError:
        ActionStep =None
        ActionList=None
        GetObjects = None


    ROS2_AVAILABLE =True
except ImportError :
    ROS2_AVAILABLE = False
    Node=object
    String= None
    ActionStep = None
    ActionList = None

    GetObjects = None


class TaskPlanner:
    def __init__ ( self,model_path :Optional[ str] = None ):
        self.backend = LLMBackend(model_path=model_path)

    def generate_plan(self, instruction: str, visible_objects: List[str]) -> List[Dict[str, Any]]:
        raw_actions=self.backend.plan(instruction , visible_objects)
        return self._validate_and_sanitize (raw_actions, visible_objects )

    def _validate_and_sanitize ( self , actions:List [Dict [str ,Any] ] , visible_objects :List [ str ])->List [Dict[str , Any ]] :

        valid_actions =[]
        for step in actions :
            action = step.get("action")
            obj_name = step.get("object_name")
            target_name= step.get( "target_name" )

            if action not in ("pick", "place", "move_to", "open_gripper", "close_gripper"):
                logger.warning(f"Discarding invalid action: {action}" )
                continue

            if action == "pick" and not obj_name:
                logger.warning ( "Pick step missing object_name, skipping." )
                continue

            if action== "place" and not target_name:
                logger.warning("Place step missing target_name, skipping.")
                continue

            valid_actions.append({
                "action": action,
                "object_name": obj_name or "" ,
                "target_name" :target_name or ""
            })
        return valid_actions


class TaskPlannerNode(Node):
    def __init__(self,model_path:Optional [ str]= None ):
        if ROS2_AVAILABLE:
            super().__init__("task_planner_node")

            self.planner = TaskPlanner( model_path= model_path)

            self.cmd_sub= self.create_subscription(
                String,
                "/user_command",
                self.command_callback,
                10
            )

            if ActionList:
                self.action_pub= self.create_publisher ( ActionList, "/planned_actions" , 10 )
            else:
                self.action_pub= self.create_publisher (String,"/planned_actions_json" , 10 )

            self.cached_objects = ["red_block", "blue_block", "green_block", "yellow_block", "red_mat", "blue_mat", "green_mat", "yellow_mat"]
            if GetObjects :
                self.perception_client= self.create_client(GetObjects ,"/get_objects")

            self.get_logger().info("TaskPlannerNode initialized and awaiting /user_command.")
        else :
            self.planner = TaskPlanner(model_path=model_path)
            logger.info ( "TaskPlanner initialized in standalone mode.")

    def command_callback(self, msg):
        instruction =msg.data
        self.get_logger ().info( f"Received user command: \"{instruction}\"")



        visible_objects= self._fetch_visible_objects ( )
        self.get_logger ( ).info(f"Context visible objects: {visible_objects}" )

        plan = self.planner.generate_plan (instruction ,visible_objects )
        self.get_logger ().info ( f"Generated plan with {len(plan)} steps: {plan}")

        self._publish_plan( plan)

    def _fetch_visible_objects(self)->List [str] :
        if ROS2_AVAILABLE and hasattr ( self ,"perception_client" )and self.perception_client.service_is_ready () :
            req= GetObjects.Request( )
            req.refresh=True
            future= self.perception_client.call_async(req )
            rclpy.spin_until_future_complete ( self,future,timeout_sec=2.0 )
            if future.result() is not None:
                return list(future.result().names)
        return self.cached_objects

    def _publish_plan(self, plan: List[Dict[str, Any]]):
        if not ROS2_AVAILABLE:
            logger.info(f"Plan (JSON): {json.dumps(plan)}")
            return

        if ActionList and ActionStep and hasattr(self, "action_pub"):

            msg = ActionList()
            for step_dict in plan :
                step = ActionStep()
                step.action= step_dict [ "action" ]
                step.object_name = step_dict["object_name"]
                step.target_name = step_dict["target_name"]
                msg.steps.append(step)
            self.action_pub.publish ( msg)

            self.get_logger().info("Published plan to /planned_actions (ActionList msg).")
        elif hasattr(self , "action_pub" ):
            json_msg= String( )
            json_msg.data = json.dumps(plan)
            self.action_pub.publish(json_msg)
            self.get_logger().info("Published plan to /planned_actions_json (JSON string).")


def main(args=None):
    if ROS2_AVAILABLE:
        rclpy.init(args= args)
        node = TaskPlannerNode()
        try :
            rclpy.spin(node)
        finally :

            node.destroy_node()
            rclpy.shutdown ()
    else:
        planner = TaskPlanner()
        cmd= "pick up the red block, place it on the blue mat"
        objects = ["red_block", "blue_mat", "green_block"]
        plan= planner.generate_plan ( cmd ,objects)
        print(f"Instruction: {cmd}" )
        print ( f"Plan: {json.dumps(plan, indent=2)}")


if __name__ == "__main__" :
    main ( )
