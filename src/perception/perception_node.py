import os
import sys
import json
import logging
from typing import List, Optional, Dict, Any
try:
    from .colour_segmentation import ColourSegmenter , DetectedObject
    from .calibrate import CameraCalibrator
    from .yolo_detector import YOLODetector
except(ImportError ,ValueError) :


    from colour_segmentation import ColourSegmenter, DetectedObject
    from calibrate import CameraCalibrator
    from yolo_detector import YOLODetector

logger = logging.getLogger("perception")


try:
    import cv2
    import numpy as np
    CV2_AVAILABLE=True
except ImportError :
    CV2_AVAILABLE =False


    cv2 = None
    np =None

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String

    try:
        from robot_arm_nlp.srv import GetObjects
    except ImportError :
        GetObjects = None
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False
    Node = object
    String = None
    GetObjects = None



class PerceptionPipeline:
    def __init__ (self, camera_index: int= 0,use_yolo : bool = False) :
        self.camera_index = camera_index
        self.segmenter=ColourSegmenter( )
        self.calibrator=CameraCalibrator( )
        self.yolo = YOLODetector( ) if use_yolo else None
        self.cap = None
        self.latest_frame = None
        self.cached_detections:List [DetectedObject ]= [ ]

    def open_camera(self) -> bool:
        if not CV2_AVAILABLE:
            return False

        # try picamera2 if on pi board
        try:
            from picamera2 import Picamera2
            self.picam2 = Picamera2 ( )
            config= self.picam2.create_preview_configuration(main={ "size" : (640,480),"format":"RGB888" } )
            self.picam2.configure(config)
            self.picam2.start()
            logger.info("Initialized Picamera2 (Pi Camera Module 3).")
            return True
        except ( ImportError,Exception ) :

            pass

        self.cap= cv2.VideoCapture( self.camera_index)
        if self.cap.isOpened( ):
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480 )
            logger.info (f"Opened OpenCV VideoCapture device {self.camera_index}" )
            return True
        logger.warning(f"Could not open camera device {self.camera_index}.")
        return False

    def capture_frame ( self ):
        if hasattr( self ,"picam2")and self.picam2 is not None :
            rgb = self.picam2.capture_array ()
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        if self.cap is not None and self.cap.isOpened():


            ret ,frame= self.cap.read()
            if ret :
                return frame

        if self.latest_frame is not None :
            return self.latest_frame

        return self._generate_synthetic_workspace ()

    def process_frame(self, frame=None) -> List[DetectedObject]:
        if frame is None :
            frame= self.capture_frame()
        self.latest_frame = frame

        if frame is None or not CV2_AVAILABLE :
            return []

        if self.yolo and self.yolo.is_available() :
            detections = self.yolo.detect(frame)
        else :
            detections = self.segmenter.detect (frame)

        h , w = frame.shape[ :2 ]
        for det in detections :
            wx, wy =self.calibrator.pixel_to_world( det.pixel_x,det.pixel_y,image_w=w ,image_h= h )
            det.world_x = wx

            det.world_y= wy
            det.world_z= 15.0 if det.obj_type== "block" else 20.0

        self.cached_detections= detections
        return detections

    def get_object( self,name: str)-> Optional [ DetectedObject]:
        for det in self.cached_detections:
            if det.name==name:
                return det

        return None

    def _generate_synthetic_workspace ( self ):
        #returns synthetic workspace for offline sim / tests
        if not CV2_AVAILABLE:
            return None

        img = np.full((480, 640, 3), 245, dtype=np.uint8)
        cv2.rectangle(img, (40, 40), (600, 440), (220, 220, 220), 2)

        # target mats: blue and yellow (area > 5000px)
        cv2.rectangle(img, (405, 125), (485, 205), (230, 120, 20), -1)
        cv2.rectangle(img, (125, 75), (205, 155), (30, 210, 230), -1)

        #target blocks: red and green (cube size ~26px)
        cv2.rectangle(img, (200, 251), (226, 277), (20, 20, 220), -1)
        cv2.rectangle ( img , ( 392 ,347), ( 418 ,373) ,( 30 , 180,30),-1)

        return img



class PerceptionNode (Node ) :
    def __init__(self):
        if ROS2_AVAILABLE:
            super().__init__("perception_node")
            self.pipeline = PerceptionPipeline()
            self.pipeline.open_camera()

            self.pub_detections= self.create_publisher ( String,"/detected_objects", 10)

            if GetObjects:
                self.srv_get_objects = self.create_service ( GetObjects,"/get_objects",self.handle_get_objects )

            self.timer = self.create_timer( 0.2 , self.timer_callback )


            self.get_logger ( ).info("PerceptionNode initialized and running at 5 Hz.")
        else:

            self.pipeline = PerceptionPipeline()
            logger.info("PerceptionPipeline initialized in standalone mode.")

    def timer_callback( self ):
        detections= self.pipeline.process_frame ()
        det_data =[
            {
                "name": d.name ,
                "type": d.obj_type,
                "color": d.color ,
                "x": round(d.world_x, 2),
                "y" :round( d.world_y,2),
                "z" :round (d.world_z , 2),
                "confidence": d.confidence
            }
            for d in detections
        ]


        msg = String( )
        msg.data = json.dumps(det_data)
        self.pub_detections.publish( msg )

    def handle_get_objects(self, request , response) :
        if request.refresh :
            detections=self.pipeline.process_frame( )
        else :
            detections = self.pipeline.cached_detections

        response.names=[d.name for d in detections]

        response.types = [d.obj_type for d in detections]
        response.x = [float( d.world_x)for d in detections ]
        response.y=[ float ( d.world_y) for d in detections ]
        response.z =[ float(d.world_z )for d in detections ]
        response.confidence =[float( d.confidence)for d in detections]
        return response


def main(args=None ) :
    if ROS2_AVAILABLE:
        rclpy.init(args=args)


        node=PerceptionNode( )
        try:
            rclpy.spin(node)
        finally :
            node.destroy_node ( )
            rclpy.shutdown()
    else:
        pipeline = PerceptionPipeline()
        detections= pipeline.process_frame ( )
        print ( f"Detected {len(detections)} objects in synthetic workspace:" )
        for d in detections:
            print(f"  - {d.name:15s}: Pixel=({d.pixel_x:.1f}, {d.pixel_y:.1f}) -> World=({d.world_x:.1f}, {d.world_y:.1f}, {d.world_z:.1f}) mm" )


if __name__== "__main__":
    main()
