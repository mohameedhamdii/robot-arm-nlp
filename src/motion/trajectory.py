import math
import logging
from dataclasses import dataclass
from typing import List, Optional
try:
    from .ik_solver import JointAngles
except ( ImportError , ValueError ):
    from ik_solver import JointAngles

logger =logging.getLogger ( __name__)


@dataclass
class TrajectoryPoint:


    angles: JointAngles
    time_s :float


class TrajectoryGenerator:
    def __init__ (self , step_delay_s:float=0.05,max_joint_vel_deg_s:float=90.0 ):

        self.step_delay_s = step_delay_s
        self.max_joint_vel_deg_s =max_joint_vel_deg_s

    def interpolate(self,start: JointAngles,goal: JointAngles, duration_s:Optional[ float ] =None) ->List[ TrajectoryPoint] :
        start_list = start.to_list()
        goal_list = goal.to_list()



        max_delta=max( abs (g -s) for s , g in zip ( start_list ,goal_list) )

        if duration_s is None:
            # clamp min duration so small moves dont jerk the servos
            duration_s = max(0.5, max_delta / self.max_joint_vel_deg_s)

        num_steps = max(2, int(duration_s / self.step_delay_s))
        trajectory: List[TrajectoryPoint] = []

        for step in range (num_steps +1) :

            t = step / float(num_steps)
            #quintic smoothstep to avoid sudden velocity jumps at ends
            s_t = 10.0 * (t ** 3) - 15.0 * (t ** 4) + 6.0 * (t ** 5)

            interp_angles = [
                s+ s_t * (g-s )
                for s,g in zip( start_list , goal_list)
            ]

            pt_angles = JointAngles(
                base_yaw= interp_angles[ 0] ,
                shoulder_pitch=interp_angles[1],
                elbow_pitch=interp_angles[2],
                wrist_pitch =interp_angles[ 3 ] ,
                wrist_roll=interp_angles[4],
                gripper =interp_angles [5]
            )

            trajectory.append(TrajectoryPoint(
                angles=pt_angles ,
                time_s = round(step*self.step_delay_s,3)
            ))

        return trajectory

    def generate_pick_and_place_waypoints( self ,start_angles: JointAngles ,pick_angles: JointAngles ,hover_pick_angles :JointAngles ,
                                          place_angles: JointAngles, hover_place_angles: JointAngles, home_angles: JointAngles) -> List[TrajectoryPoint]:
        full_trajectory:List [TrajectoryPoint]=[ ]

        current_time = 0.0

        # sequence: hover over pick -> drop down -> clamp -> lift -> swing to place -> drop -> open -> retract -> home
        segments= [
            (hover_pick_angles, 1.2),
            ( pick_angles , 0.8),
            ( JointAngles (
                base_yaw=pick_angles.base_yaw,
                shoulder_pitch=pick_angles.shoulder_pitch,
                elbow_pitch = pick_angles.elbow_pitch ,
                wrist_pitch =pick_angles.wrist_pitch ,
                wrist_roll=pick_angles.wrist_roll,
                gripper=110.0
            ),0.5 ),
            (JointAngles (
                base_yaw = hover_pick_angles.base_yaw,
                shoulder_pitch =hover_pick_angles.shoulder_pitch ,
                elbow_pitch=hover_pick_angles.elbow_pitch,
                wrist_pitch=hover_pick_angles.wrist_pitch ,
                wrist_roll=hover_pick_angles.wrist_roll ,
                gripper=110.0
            ) , 0.8 ) ,
            (JointAngles(
                base_yaw=hover_place_angles.base_yaw ,
                shoulder_pitch=hover_place_angles.shoulder_pitch,
                elbow_pitch = hover_place_angles.elbow_pitch ,
                wrist_pitch= hover_place_angles.wrist_pitch,
                wrist_roll = hover_place_angles.wrist_roll,
                gripper = 110.0
            ),1.5 ),
            (JointAngles(
                base_yaw=place_angles.base_yaw,
                shoulder_pitch =place_angles.shoulder_pitch,
                elbow_pitch = place_angles.elbow_pitch ,
                wrist_pitch =place_angles.wrist_pitch ,
                wrist_roll= place_angles.wrist_roll,
                gripper =110.0
            ) ,0.8 ),
            (place_angles, 0.5),
            (hover_place_angles, 0.8),
            (home_angles, 1.2)
        ]

        curr_state = start_angles
        for target, dur in segments:
            seg_pts = self.interpolate(curr_state, target, duration_s=dur)
            for p in seg_pts:
                full_trajectory.append( TrajectoryPoint(
                    angles=p.angles,
                    time_s= round ( current_time+p.time_s,3)
                ))
            current_time += dur
            curr_state = target

        return full_trajectory
