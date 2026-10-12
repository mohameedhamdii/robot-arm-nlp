import os
import math
import yaml
import logging
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class WorkspaceLimitError(ValueError ) :
    pass




@dataclass
class JointAngles :
    base_yaw:float       #servo 0, deg [0..180], 90 centered
    shoulder_pitch: float #servo 1, deg [15..165]
    elbow_pitch : float    #servo 2, deg [15..165]

    wrist_pitch :float    # servo 3, deg [0..180]
    wrist_roll: float     # servo 4, deg [0..180]
    gripper: float        #servo 5, deg [0..180] (30 open, 110 closed)

    def to_list( self)-> list :
        return [
            self.base_yaw,
            self.shoulder_pitch ,
            self.elbow_pitch,
            self.wrist_pitch,
            self.wrist_roll,
            self.gripper
        ]



    def to_dict(self) -> Dict[str, float]:
        return {
            "base_yaw" : round (self.base_yaw,2 ),
            "shoulder_pitch": round(self.shoulder_pitch, 2),
            "elbow_pitch": round(self.elbow_pitch, 2),
            "wrist_pitch":round ( self.wrist_pitch ,2 ) ,
            "wrist_roll":round (self.wrist_roll ,2 ) ,
            "gripper":round ( self.gripper , 2)
        }


class IKSolver :
    def __init__(self,dimensions_path : Optional [str]=None,calibration_path:Optional [ str]= None ):
        self.dim_path = dimensions_path or os.path.join(
            os.path.dirname(__file__), "..", "..", "config", "arm_dimensions.yaml"
        )
        self.calib_path= calibration_path or os.path.join (
            os.path.dirname(__file__), "..", "..", "config", "servo_calibration.yaml"
        )

        self.load_config( )

    def load_config(self):
        if os.path.exists( self.dim_path):
            with open (self.dim_path,"r") as f :
                data = yaml.safe_load(f)
                self.base_height =float ( data.get ( "base_height",65.0 ) )
                self.shoulder_length = float(data.get("shoulder_length", 105.0))
                self.elbow_length=float( data.get ( "elbow_length" ,100.0 ))

                self.wrist_length= float(data.get ( "wrist_length" ,70.0 ))
                self.gripper_length =float( data.get("gripper_length" , 55.0 ) )
                self.workspace = data.get("workspace", {
                    "x_min" :-150.0 , "x_max" : 150.0,
                    "y_min" :50.0 , "y_max": 250.0 ,
                    "z_min": 0.0, "z_max": 200.0
                })
        else:
            self.base_height =65.0
            self.shoulder_length = 105.0
            self.elbow_length = 100.0
            self.wrist_length=70.0
            self.gripper_length=55.0
            self.workspace= {
                "x_min":- 150.0 , "x_max" :150.0 ,
                "y_min": 50.0, "y_max": 250.0,
                "z_min": 0.0, "z_max": 200.0
            }

        #physical travel limits on servos to prevent binding
        self.joint_limits={
            "base_yaw": (0.0, 180.0),
            "shoulder_pitch": (15.0, 165.0 ) ,
            "elbow_pitch": (15.0, 165.0),
            "wrist_pitch":(0.0,180.0) ,
            "wrist_roll": (0.0, 180.0),
            "gripper" : (0.0, 180.0)
        }

    def check_workspace ( self , x : float,y: float , z:float )-> bool :
        ws =self.workspace
        if not(ws["x_min"]<= x<= ws ["x_max"] ) :
            raise WorkspaceLimitError (f"X={x:.1f} out of workspace bounds [{ws['x_min']}, {ws['x_max']}]")
        if not( ws[ "y_min" ] <= y<=ws["y_max" ] ) :
            raise WorkspaceLimitError( f"Y={y:.1f} out of workspace bounds [{ws['y_min']}, {ws['y_max']}]" )
        if not ( ws [ "z_min"]<=z<= ws ["z_max"] ) :
            raise WorkspaceLimitError( f"Z={z:.1f} out of workspace bounds [{ws['z_min']}, {ws['z_max']}]")
        return True

    def solve_ik( self ,x : float ,y: float,z:float ,pitch_deg :float = -90.0, roll_deg :float =0.0 , gripper_angle:float= 30.0 ) ->JointAngles :

        self.check_workspace (x,y , z)

        # base azimuth on ground plane
        base_angle_rad=math.atan2( x ,y)
        base_servo_deg = 90.0+math.degrees (base_angle_rad)
        r = math.hypot(x, y)

        total_wrist_len = self.wrist_length + self.gripper_length
        L1 = self.shoulder_length
        L2 = self.elbow_length
        max_reach = L1 + L2
        min_reach = abs(L1 - L2)

        #try commanded pitch first, relax if geometric triangle unreachable
        candidate_pitches=[ pitch_deg ]
        if pitch_deg ==- 90.0 :
            candidate_pitches.extend(range(-85, -5, 5))

        chosen_pitch_rad =None
        chosen_D_sq = None


        chosen_rw = None
        chosen_dz = None

        for cand_deg in candidate_pitches :
            cand_rad = math.radians(cand_deg)
            r_w=r -total_wrist_len * math.cos(cand_rad)
            z_w =z-total_wrist_len*math.sin(cand_rad )
            dz =z_w-self.base_height
            D_sq = r_w**2 + dz**2
            D = math.sqrt(D_sq)

            if min_reach <= D <= max_reach:
                chosen_pitch_rad= cand_rad
                chosen_D_sq= D_sq
                chosen_rw = r_w
                chosen_dz=dz
                break

        if chosen_pitch_rad is None:
            raise WorkspaceLimitError( f"Target unreachable: No valid kinematic solution at ({x:.1f}, {y:.1f}, {z:.1f})" )

        pitch_rad = chosen_pitch_rad
        D_sq = chosen_D_sq

        r_w = chosen_rw
        dz = chosen_dz
        D=math.sqrt( D_sq)

        #law of cosines on planar triangle
        cos_beta = (L1**2 + L2**2 - D_sq) / (2.0 * L1 * L2)
        cos_beta=max( -1.0,min ( 1.0 ,cos_beta))
        beta =math.acos(cos_beta )

        elbow_angle_deg = math.degrees( math.pi - beta)
        elbow_servo_deg= 180.0 -elbow_angle_deg


        #shoulder elevation angle
        alpha1= math.atan2 ( dz, r_w )
        cos_alpha2 = (L1**2 + D_sq - L2**2) / (2.0 * L1 * D)
        cos_alpha2 =max(- 1.0,min ( 1.0, cos_alpha2 ))
        alpha2= math.acos (cos_alpha2 )

        shoulder_angle_rad =alpha1 +alpha2
        shoulder_servo_deg =math.degrees ( shoulder_angle_rad)

        #wrist pitch to keep end effector at requested pitch_rad
        forearm_orientation_rad= shoulder_angle_rad- ( math.pi- beta)
        wrist_relative_rad = pitch_rad-forearm_orientation_rad
        wrist_servo_deg =180.0+ math.degrees ( wrist_relative_rad )

        wrist_roll_deg= 90.0 + roll_deg

        angles = JointAngles(
            base_yaw=self._clamp("base_yaw" , base_servo_deg ),
            shoulder_pitch=self._clamp( "shoulder_pitch" , shoulder_servo_deg),
            elbow_pitch=self._clamp("elbow_pitch", elbow_servo_deg),
            wrist_pitch= self._clamp ( "wrist_pitch" , wrist_servo_deg ),
            wrist_roll=self._clamp( "wrist_roll" , wrist_roll_deg) ,
            gripper = self._clamp ("gripper" , gripper_angle )
        )

        return angles

    def solve_fk(self, angles: JointAngles) -> Tuple[float, float, float]:
        base_angle_rad = math.radians(angles.base_yaw - 90.0)
        shoulder_rad =math.radians ( angles.shoulder_pitch)

        elbow_deflection_deg =180.0-angles.elbow_pitch
        forearm_rad = shoulder_rad -math.radians(elbow_deflection_deg )

        wrist_rel_deg= angles.wrist_pitch-180.0
        pitch_rad= forearm_rad +math.radians( wrist_rel_deg)

        L1= self.shoulder_length
        L2 = self.elbow_length


        L_wrist =self.wrist_length + self.gripper_length


        # forward radial projection
        r =( L1* math.cos(shoulder_rad) +
             L2 * math.cos ( forearm_rad )+
             L_wrist* math.cos(pitch_rad ))

        z = (self.base_height +
             L1*math.sin( shoulder_rad)+
             L2* math.sin( forearm_rad ) +
             L_wrist * math.sin(pitch_rad))

        x = r * math.sin(base_angle_rad)
        y = r * math.cos(base_angle_rad)

        return float (x ) , float ( y) , float(z)



    def _clamp( self, joint_name:str, val: float) ->float :
        min_v, max_v = self.joint_limits.get(joint_name, (0.0, 180.0))
        return max(min_v , min ( max_v ,float(val )))
