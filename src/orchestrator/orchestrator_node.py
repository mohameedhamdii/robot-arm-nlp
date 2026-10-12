import os
import sys
import time
import json
import logging
from typing import Optional, List, Dict, Any, Callable

try:
    from ..task_planner.task_planner_node import TaskPlanner
    from ..perception.perception_node import PerceptionPipeline


    from ..motion.motion_node import MotionController
    from ..perception.colour_segmentation import DetectedObject
except( ImportError, ValueError):
    from src.task_planner.task_planner_node import TaskPlanner
    from src.perception.perception_node import PerceptionPipeline

    from src.motion.motion_node import MotionController
    from src.perception.colour_segmentation import DetectedObject

logger = logging.getLogger ( "orchestrator")

try :
    import rclpy


    from rclpy.node import Node
    from std_msgs.msg import String
    try :
        from robot_arm_nlp.msg import ActionList, ActionStep
        from robot_arm_nlp.srv import GetObjects
    except ImportError :
        ActionList=None

        ActionStep= None
        GetObjects = None
    ROS2_AVAILABLE=True
except ImportError:
    ROS2_AVAILABLE = False
    Node = object
    String =None
    ActionList = None
    ActionStep = None

    GetObjects = None


class OrchestratorPipeline:
    def __init__ ( self,
                 planner: Optional[TaskPlanner] = None,
                 perception: Optional[PerceptionPipeline] = None,
                 motion: Optional[ MotionController] = None,
                 force_mock_hardware: bool = False ):
        self.planner =planner or TaskPlanner()
        self.perception= perception or PerceptionPipeline ( )
        self.motion=motion or MotionController(force_mock=force_mock_hardware)

    def scan_workspace(self, retries: int = 3) -> List[DetectedObject]:
        for attempt in range(1, retries + 1):
            detections= self.perception.process_frame ()
            if detections:
                return detections
            logger.info( f"Scan attempt {attempt}/{retries}: No objects detected, re-scanning..." )
            time.sleep(0.3)
        return[]

    def execute_instruction ( self, instruction: str,progress_callback :Optional[Callable[ [ str ,Any ] , None ]]= None )->Dict[ str , Any ]:
        start_time = time.time()
        result ={
            "instruction": instruction,
            "status": "in_progress",
            "steps_total": 0 ,
            "steps_completed" :0 ,
            "errors": [],
            "actions": []
        }

        if progress_callback:
            progress_callback("SCANNING", "Scanning workspace objects via camera...")

        detections =self.scan_workspace( retries = 3 )

        visible_names =[d.name for d in detections ]
        logger.info ( f"Visible objects detected ({len(visible_names)}): {visible_names}" )

        if progress_callback:
            progress_callback("PLANNING", f"Generating LLM action plan for visible: {visible_names}")

        actions= self.planner.generate_plan( instruction ,visible_names )
        result ["actions"] =actions
        result["steps_total"]=len (actions)

        if not actions :
            err = f"Could not generate valid action plan for instruction: '{instruction}'"
            logger.error ( err )
            result[ "status"] ="failed"
            result["errors"].append(err)
            if progress_callback :
                progress_callback("FAILED", err)


            return result

        logger.info( f"Plan generated with {len(actions)} steps: {actions}")

        #dispatch atomic pick & place pairs
        i = 0
        while i<len (actions) :
            action_item = actions[i]
            act=action_item[ "action" ]

            if act =="pick":
                pick_obj_name =action_item [ "object_name" ]
                place_target_name = None

                if i +1<len ( actions )and actions[ i+ 1 ] ["action"]=="place":
                    place_target_name=actions [i + 1][ "target_name" ]
                    i +=2
                else:
                    i+= 1

                pick_obj= self._locate_object_with_retry ( pick_obj_name )
                if not pick_obj:
                    err = f"Object '{pick_obj_name}' not found on workspace after rescanning."
                    result["errors"].append(err)
                    result["status"] = "failed"
                    if progress_callback:

                        progress_callback("FAILED", err)
                    return result

                place_obj = None
                if place_target_name:
                    place_obj=self._locate_object_with_retry ( place_target_name )
                    if not place_obj:
                        err= f"Destination '{place_target_name}' not found on workspace."
                        result["errors"].append(err)

                        result["status"] = "failed"
                        if progress_callback:
                            progress_callback ( "FAILED" , err )
                        return result
                    place_x, place_y = place_obj.world_x, place_obj.world_y
                else:
                    place_x,place_y= 0.0 ,150.0

                msg= f"Executing: Pick {pick_obj_name} ({pick_obj.world_x:.1f}, {pick_obj.world_y:.1f}) -> Place on {place_target_name or 'center'} ({place_x:.1f}, {place_y:.1f})"
                logger.info(msg)
                if progress_callback:
                    progress_callback("EXECUTING", msg)

                try :

                    success= self.motion.execute_pick_and_place(
                        pick_x= pick_obj.world_x ,
                        pick_y= pick_obj.world_y ,
                        place_x=place_x,
                        place_y =place_y
                    )
                    if not success:
                        err= "Motion execution failed or was interrupted by E-STOP."
                        result["errors"].append( err)
                        result["status"] = "failed"
                        if progress_callback :
                            progress_callback("FAILED", err)
                        return result

                    result[ "steps_completed" ]+=2 if place_target_name else 1
                except Exception as e :
                    err =f"Kinematics / Motion error: {str(e)}"


                    logger.error (err )

                    result ["errors"].append( err )
                    result["status"] = "failed"
                    if progress_callback :
                        progress_callback( "FAILED" ,err)
                    return result
            else:


                i += 1

        result["status"]= "success"
        result ["duration_s"] = round(time.time ()- start_time,2 )
        if progress_callback :
            progress_callback ("COMPLETED" , f"Successfully completed all steps in {result['duration_s']}s." )
        return result

    def _locate_object_with_retry(self, name: str, retries: int = 3) -> Optional[DetectedObject]:
        for attempt in range( retries):

            for d in self.perception.cached_detections :
                if d.name == name or d.color in name:
                    return d
            self.perception.process_frame( )
            for d in self.perception.cached_detections :
                if d.name==name or d.color in name:
                    return d
            time.sleep(0.2)
        return None




class OrchestratorNode(Node):
    def __init__ (self):
        if ROS2_AVAILABLE:
            super().__init__( "orchestrator_node" )
            self.orchestrator=OrchestratorPipeline()

            self.sub_plan =self.create_subscription (
                String ,
                "/planned_actions_json" ,
                self.plan_callback,
                10
            )
            self.pub_result=self.create_publisher ( String , "/task_result" , 10)
            self.get_logger().info ("OrchestratorNode initialized." )
        else:
            self.orchestrator = OrchestratorPipeline()
            logger.info("Orchestrator initialized in standalone mode." )

    def plan_callback(self, msg : String):
        try:
            plan = json.loads(msg.data)
            self.get_logger().info(f"Received action plan to execute: {plan}")
        except Exception as e:
            self.get_logger ().error(f"Error handling action plan: {e}" )


def main(args=None):
    if ROS2_AVAILABLE :

        rclpy.init (args = args )
        node = OrchestratorNode()
        try:
            rclpy.spin( node )
        finally:
            node.destroy_node ( )
            rclpy.shutdown( )
    else :
        pipeline =OrchestratorPipeline ( force_mock_hardware =True)
        command= "pick up the red block and place it on the blue mat"
        print(f"Testing Orchestrator with command: \"{command}\"" )
        res =pipeline.execute_instruction (
            command ,
            progress_callback=lambda stage, msg: print(f"[{stage:10s}] {msg}")
        )

        print("Pipeline Result:" , json.dumps( res ,indent =2 ))



if __name__ == "__main__":
    main( )
