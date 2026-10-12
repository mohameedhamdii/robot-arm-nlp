import math
from typing import Dict, List, Tuple
try:
    from ..motion.ik_solver import JointAngles,IKSolver
except( ImportError,ValueError ) :
    from src.motion.ik_solver import JointAngles, IKSolver


class VirtualArm :
    def __init__(self):
        self.ik= IKSolver( )
        self.current_angles =JointAngles ( 90.0, 90.0,90.0,90.0 , 90.0,30.0)



    def set_angles(self, angles :JointAngles) :
        self.current_angles = angles

    def get_joint_positions_3d ( self ) ->List [Dict [ str,float] ]:
        angles= self.current_angles

        base_angle_rad = math.radians(angles.base_yaw - 90.0)
        shoulder_rad= math.radians (angles.shoulder_pitch)

        elbow_deflection_deg=180.0-angles.elbow_pitch
        forearm_rad = shoulder_rad - math.radians(elbow_deflection_deg)

        wrist_rel_deg = angles.wrist_pitch - 180.0


        pitch_rad = forearm_rad + math.radians(wrist_rel_deg)

        L0 = self.ik.base_height       #65 mm
        L1=self.ik.shoulder_length   #105 mm
        L2 = self.ik.elbow_length      #100 mm
        L3 = self.ik.wrist_length      # 70 mm
        L4=self.ik.gripper_length    #55 mm


        p0={ "x":0.0, "y": 0.0,"z": 0.0 , "name":"base" }
        p1={ "x": 0.0 , "y":0.0,"z": L0 ,"name" :"shoulder"}

        #elbow pivot
        r1 = L1 * math.cos (shoulder_rad)
        z1 =L0 +L1 *math.sin( shoulder_rad )
        x1 = r1 * math.sin(base_angle_rad)
        y1 = r1 * math.cos(base_angle_rad)
        p2 = {"x" : round (x1,2 ),"y": round ( y1, 2 ),"z" :round (z1 , 2), "name" : "elbow" }

        #wrist pitch
        r2 = r1 + L2 * math.cos(forearm_rad)

        z2 =z1+L2* math.sin ( forearm_rad)
        x2 = r2 * math.sin(base_angle_rad)
        y2=r2*math.cos(base_angle_rad)
        p3 = {"x": round (x2, 2 ), "y": round(y2 ,2),"z" : round (z2 , 2 ) ,"name": "wrist_pitch" }

        #wrist roll / gripper mount
        r3 = r2 + L3 * math.cos(pitch_rad)
        z3= z2 + L3 *math.sin (pitch_rad)
        x3 = r3 * math.sin(base_angle_rad)
        y3 =r3* math.cos ( base_angle_rad)
        p4 ={ "x":round (x3, 2 ) , "y" :round( y3 , 2 ), "z": round (z3 , 2), "name":"gripper_mount"}

        #tcp endpoint
        r4=r3 +L4* math.cos ( pitch_rad )
        z4 = z3 + L4 * math.sin(pitch_rad)
        x4= r4* math.sin( base_angle_rad)
        y4 =r4 *math.cos(base_angle_rad )
        p5 = {"x": round(x4, 2), "y": round(y4, 2), "z": round(z4, 2), "name": "tcp"}

        return[p0 , p1 ,p2,p3,p4, p5 ]
