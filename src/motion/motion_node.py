import os
import sys
import time
import json
import logging
from typing import Optional, Callable, Dict, Any

try:
    from .ik_solver import IKSolver, JointAngles , WorkspaceLimitError
    from .trajectory import TrajectoryGenerator,TrajectoryPoint


    from .servo_driver import get_servo_driver,BaseServoDriver
except( ImportError ,ValueError ):
    from ik_solver import IKSolver, JointAngles, WorkspaceLimitError
    from trajectory import TrajectoryGenerator, TrajectoryPoint
    from servo_driver import get_servo_driver , BaseServoDriver


logger = logging.getLogger ("motion")

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String ,Bool


    ROS2_AVAILABLE =True
except ImportError:
    ROS2_AVAILABLE =False
    Node= object
    String = None
    Bool = None


class MotionController:

    def __init__(self, driver: Optional[BaseServoDriver] = None, force_mock: bool = False):
        self.ik = IKSolver ()
        self.trajectory_gen = TrajectoryGenerator(step_delay_s=0.05)
        self.driver = driver or get_servo_driver(force_mock=force_mock)
        self.is_stopped = False

        # clearance and approach heights in mm
        self.hover_height=80.0
        self.grasp_height= 15.0
        self.place_height=20.0

        self.home_pos= ( 0.0 ,120.0 , 100.0)

    def emergency_stop(self):
        self.is_stopped = True
        logger.warning( "EMERGENCY STOP ACTIVATED! Motion halted.")

    def reset_estop(self):
        self.is_stopped =False

    def execute_trajectory(self, trajectory: list, step_callback: Optional[Callable[[JointAngles], None]] = None) -> bool:
        for pt in trajectory :
            if self.is_stopped :
                logger.warning("Trajectory aborted due to E-STOP.")
                return False

            self.driver.set_joint_angles(pt.angles )
            if step_callback:
                step_callback ( pt.angles )
            time.sleep( self.trajectory_gen.step_delay_s)
        return True

    def move_to(self, x : float,y:float,z:float , duration_s:Optional [ float]= None ,
                gripper_deg: Optional[float] = None, step_callback: Optional[Callable] = None) -> bool:
        current_angles= self.driver.get_current_angles( )
        target_gripper=gripper_deg if gripper_deg is not None else current_angles.gripper
        target_angles = self.ik.solve_ik(x, y, z, pitch_deg=-90.0, gripper_angle=target_gripper)


        traj =self.trajectory_gen.interpolate(current_angles, target_angles , duration_s= duration_s )
        return self.execute_trajectory ( traj,step_callback = step_callback)

    def open_gripper(self , step_callback : Optional[ Callable]= None)-> bool :
        curr = self.driver.get_current_angles()
        target = JointAngles(
            base_yaw =curr.base_yaw ,
            shoulder_pitch= curr.shoulder_pitch,
            elbow_pitch= curr.elbow_pitch,
            wrist_pitch= curr.wrist_pitch ,
            wrist_roll=curr.wrist_roll,
            gripper = 30.0
        )
        traj =self.trajectory_gen.interpolate( curr , target ,duration_s =0.4 )
        return self.execute_trajectory(traj, step_callback=step_callback)

    def close_gripper (self , step_callback:Optional [Callable]=None)-> bool:
        curr = self.driver.get_current_angles()
        target= JointAngles (
            base_yaw=curr.base_yaw,
            shoulder_pitch = curr.shoulder_pitch,
            elbow_pitch =curr.elbow_pitch ,
            wrist_pitch= curr.wrist_pitch,
            wrist_roll =curr.wrist_roll ,
            gripper=110.0
        )
        traj= self.trajectory_gen.interpolate(curr , target ,duration_s=0.4)
        return self.execute_trajectory(traj , step_callback =step_callback)

    def go_home (self , step_callback : Optional [ Callable]=None ) -> bool:
        hx, hy, hz = self.home_pos


        return self.move_to(hx,hy,hz, duration_s= 1.5 ,gripper_deg= 30.0 , step_callback=step_callback)

    def execute_pick_and_place (self , pick_x : float,pick_y:float , place_x :float , place_y : float ,
                               step_callback :Optional[Callable] = None)-> bool :
        logger.info( f"Starting Pick and Place: ({pick_x:.1f}, {pick_y:.1f}) -> ({place_x:.1f}, {place_y:.1f})")
        self.reset_estop()

        if not self.open_gripper(step_callback):
            return False

        if not self.move_to(pick_x, pick_y, self.hover_height, duration_s=1.2, step_callback=step_callback):
            return False

        if not self.move_to(pick_x, pick_y, self.grasp_height, duration_s=0.8, step_callback=step_callback):
            return False

        if not self.close_gripper(step_callback):
            return False
        time.sleep(0.1)

        # lift before lateral translation so we dont sweep workspace
        if not self.move_to( pick_x ,pick_y , self.hover_height ,duration_s= 0.8,step_callback=step_callback ):
            return False

        if not self.move_to (place_x , place_y,self.hover_height , duration_s= 1.5, step_callback =step_callback):
            return False

        if not self.move_to(place_x, place_y, self.place_height, duration_s=0.8, step_callback=step_callback):
            return False


        if not self.open_gripper ( step_callback ):
            return False
        time.sleep(0.1)

        if not self.move_to(place_x, place_y, self.hover_height, duration_s=0.8, step_callback=step_callback):
            return False

        if not self.go_home(step_callback):
            return False

        logger.info ( "Pick and Place sequence successfully completed!")

        return True


class MotionNode(Node):
    def __init__(self ) :
        if ROS2_AVAILABLE:
            super().__init__( "motion_node" )
            self.controller = MotionController()

            self.sub_estop = self.create_subscription(Bool, "/estop", self.estop_callback, 10)
            self.sub_cmd = self.create_subscription(String, "/motion_command", self.cmd_callback, 10)
            self.pub_telemetry=self.create_publisher ( String,"/arm_telemetry" ,10)

            self.get_logger ().info( "MotionNode initialized." )
        else :
            self.controller= MotionController ( )

            logger.info("MotionController initialized in standalone mode.")

    def estop_callback( self,msg :Bool ) :
        if msg.data:
            self.controller.emergency_stop()
        else:
            self.controller.reset_estop()

    def cmd_callback (self,msg:String):
        try:
            cmd = json.loads(msg.data)
            action= cmd.get( "action" )
            if action =="pick_and_place":


                self.controller.execute_pick_and_place(
                    cmd [ "pick_x" ] , cmd ["pick_y"],
                    cmd["place_x"], cmd["place_y"],
                    step_callback =self._telemetry_callback
                )
            elif action =="home":

                self.controller.go_home( step_callback=self._telemetry_callback)
        except Exception as e :
            self.get_logger ( ).error(f"Error executing motion command: {e}")

    def _telemetry_callback (self,angles : JointAngles ):
        if ROS2_AVAILABLE and hasattr ( self ,"pub_telemetry") :
            msg =String ( )


            msg.data = json.dumps(angles.to_dict())
            self.pub_telemetry.publish( msg )


def main (args = None ):
    if ROS2_AVAILABLE:
        rclpy.init(args =args)
        node = MotionNode( )
        try :
            rclpy.spin(node)
        finally:

            node.destroy_node()
            rclpy.shutdown ( )
    else:
        controller = MotionController( force_mock= True)
        print ( "Testing Motion Controller Pick & Place:")
        success= controller.execute_pick_and_place(
            pick_x =- 50.0 ,pick_y =140.0 ,
            place_x =60.0, place_y=180.0 ,
            step_callback = lambda a :print ( f"  Step -> base:{a.base_yaw:.1f} shldr:{a.shoulder_pitch:.1f} elbw:{a.elbow_pitch:.1f} grp:{a.gripper:.1f}" )
        )
        print(f"Result: {'SUCCESS' if success else 'FAILED'}")


if __name__== "__main__" :
    main()
