import os
import time
import yaml
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict
try:
    from .ik_solver import JointAngles
except(ImportError,ValueError):
    from ik_solver import JointAngles



logger=logging.getLogger (__name__ )


class BaseServoDriver(ABC):
    @abstractmethod
    def set_joint_angles(self ,angles:JointAngles ):
        pass


    @ abstractmethod
    def set_channel_angle(self, channel : int,angle :float) :
        pass

    @abstractmethod
    def get_current_angles( self ) ->JointAngles:
        pass

    @abstractmethod
    def close(self):


        pass


class MockServoDriver(BaseServoDriver ) :
    def __init__( self,initial_angles : Optional [ JointAngles ] =None) :
        self.current_angles = initial_angles or JointAngles(
            base_yaw=90.0,
            shoulder_pitch=90.0,
            elbow_pitch=90.0,
            wrist_pitch= 90.0,
            wrist_roll=90.0,
            gripper=30.0
        )
        self.command_log =[]
        logger.info ( "Initialized MockServoDriver (Simulation Mode)." )


    def set_joint_angles (self , angles :JointAngles):
        self.current_angles =angles
        self.command_log.append(angles.to_dict ( ) )

    def set_channel_angle(self, channel: int, angle: float):
        angles_list = self.current_angles.to_list()
        if 0<= channel <6:
            angles_list[channel] = angle
            self.current_angles =JointAngles (* angles_list )


    def get_current_angles(self) -> JointAngles:
        return self.current_angles

    def close(self ) :
        logger.info ( "MockServoDriver closed.")


class PCA9685ServoDriver(BaseServoDriver):
    def __init__ (self,config_path: Optional [ str]=None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__) , "..",".." , "config","servo_calibration.yaml"
        )
        self.kit = None
        self.servos_cfg= {}
        self.current_angles = JointAngles(90.0, 90.0, 90.0, 90.0, 90.0, 30.0)
        self._init_hardware ()

    def _init_hardware( self):
        if os.path.exists(self.config_path):
            with open(self.config_path , "r" )as f :
                data = yaml.safe_load (f)
                self.servos_cfg = data.get("servos", { } )
                self.i2c_bus = data.get("i2c_bus", 1)
                self.i2c_address = data.get("i2c_address", 0x40)
        else :
            self.servos_cfg= {}

        try:

            from adafruit_servokit import ServoKit
            self.kit =ServoKit( channels = 16, address= self.i2c_address)

            for joint_name, cfg in self.servos_cfg.items():
                ch= cfg.get("channel" )
                min_us = cfg.get ( "min_pulse_us",500 )
                max_us = cfg.get("max_pulse_us", 2500)
                if ch is not None and 0 <= ch <16 :
                    self.kit.servo[ch].set_pulse_width_range(min_us, max_us)
                    self.kit.servo[ ch ].actuation_range= 180

            logger.info("Connected to PCA9685 servo driver via I2C.")
        except Exception as e :
            logger.error(f"Failed to connect to physical PCA9685: {e}. Raising for fallback." )
            raise

    def set_joint_angles(self,angles:JointAngles ):
        joint_values= [
            ( "base_yaw" , angles.base_yaw) ,
            ("shoulder_pitch" ,angles.shoulder_pitch ),
            ( "elbow_pitch", angles.elbow_pitch),
            ("wrist_pitch" ,angles.wrist_pitch) ,
            ( "wrist_roll" ,angles.wrist_roll),
            ("gripper",angles.gripper )
        ]


        for name , deg in joint_values:
            cfg= self.servos_cfg.get( name , { } )
            ch =cfg.get("channel" )
            offset = cfg.get("center_offset_deg", 0.0)
            is_inverted = cfg.get("inverted", False)

            target_deg = deg + offset
            if is_inverted:
                target_deg = 180.0 - target_deg

            min_ang = cfg.get("min_angle", 0.0)
            max_ang = cfg.get("max_angle" ,180.0 )
            clamped_deg = max(min_ang,min(max_ang, target_deg) )

            if ch is not None and self.kit is not None:
                self.kit.servo [ch].angle = clamped_deg

        self.current_angles = angles

    def set_channel_angle(self, channel: int, angle: float):
        if self.kit is not None and 0 <= channel < 16:
            self.kit.servo [channel].angle= max( 0.0 , min (180.0,angle) )

    def get_current_angles(self) -> JointAngles:
        return self.current_angles


    def close ( self) :
        if self.kit is not None :
            for ch in range ( 6 ) :
                try:
                    self.kit.servo[ch].angle = None
                except Exception:
                    pass
            logger.info("PCA9685 servos relaxed.")


def get_servo_driver( force_mock :bool= False )-> BaseServoDriver:

    if force_mock:
        return MockServoDriver ( )
    try:
        return PCA9685ServoDriver( )
    except Exception as e:
        logger.info ( f"Using MockServoDriver (hardware unavailable: {e})")
        return MockServoDriver( )


ServoDriver = PCA9685ServoDriver

__all__=[
    "BaseServoDriver", "MockServoDriver", "PCA9685ServoDriver", "ServoDriver", "get_servo_driver"
]
