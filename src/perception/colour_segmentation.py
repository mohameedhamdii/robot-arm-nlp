import os
import yaml
import logging
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np


    CV2_AVAILABLE =True
except ImportError:
    CV2_AVAILABLE= False
    cv2 = None
    np= None



@dataclass
class DetectedObject:
    name: str              #red_block, blue_mat, etc
    color : str             #red, blue...
    obj_type: str          #block or mat
    pixel_x: float         #centroid X


    pixel_y :float         #centroid Y
    world_x :float=0.0   # world mm
    world_y: float = 0.0
    world_z: float = 0.0
    confidence: float = 1.0
    area_px: float = 0.0

    bbox:Tuple [ int, int,int , int ] = ( 0,0 ,0 ,0 )


class ColourSegmenter:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path=config_path or os.path.join (
            os.path.dirname ( __file__ ), ".." , "..","config", "colour_ranges.yaml"
        )
        self.colors_config={}
        self.detection_config = { }
        self.load_config( )

    def load_config(self):

        if os.path.exists(self.config_path):
            with open (self.config_path, "r") as f:
                data = yaml.safe_load(f)
                self.colors_config = data.get("colours" , { } )
                self.detection_config = data.get("detection", {})
        else:
            logger.warning (f"Config {self.config_path} not found, using default HSV bounds.")
            self.colors_config = {
                "red":{
                    "hsv_lower": [0, 120, 70],
                    "hsv_upper" : [ 10,255,255],
                    "hsv_lower_2":[ 170 ,120, 70 ],
                    "hsv_upper_2": [ 180, 255, 255]
                },
                "blue": {
                    "hsv_lower":[100, 120 , 70] ,
                    "hsv_upper": [130, 255, 255]
                } ,
                "green" : {
                    "hsv_lower":[ 40 ,70,70 ] ,
                    "hsv_upper": [80, 255, 255]
                },
                "yellow" : {
                    "hsv_lower": [20, 100,100 ] ,
                    "hsv_upper" :[ 35, 255,255 ]
                }
            }
            self.detection_config={
                "min_contour_area_block": 500,
                "max_contour_area_block" : 5000 ,
                "min_contour_area_mat" : 5000,
                "max_contour_area_mat": 50000,
                "gaussian_blur_kernel": 5 ,
                "morph_kernel_size": 3
            }

    def detect ( self, bgr_image) -> List[ DetectedObject ]:
        if not CV2_AVAILABLE or bgr_image is None:
            return[ ]

        ksize=int(self.detection_config.get("gaussian_blur_kernel" ,5) )
        if ksize % 2 ==0 :
            ksize+= 1
        blurred= cv2.GaussianBlur( bgr_image, (ksize,ksize ),0 )
        hsv = cv2.cvtColor(blurred,cv2.COLOR_BGR2HSV)

        detected_objects: List [ DetectedObject]= []
        morph_k = int ( self.detection_config.get ( "morph_kernel_size",3) )
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT ,( morph_k , morph_k))

        min_block_area=self.detection_config.get("min_contour_area_block", 500)

        max_block_area = self.detection_config.get("max_contour_area_block" , 5000 )
        min_mat_area=self.detection_config.get( "min_contour_area_mat", 5000 )
        max_mat_area = self.detection_config.get("max_contour_area_mat",50000 )

        for color_name, bounds in self.colors_config.items():
            lower1 = np.array(bounds["hsv_lower"], dtype=np.uint8)
            upper1 = np.array(bounds["hsv_upper"], dtype=np.uint8)
            mask = cv2.inRange(hsv, lower1, upper1)

            # red wraps around 0/180 hue boundary
            if "hsv_lower_2" in bounds and "hsv_upper_2" in bounds:
                lower2 = np.array(bounds["hsv_lower_2"], dtype=np.uint8)
                upper2 = np.array( bounds [ "hsv_upper_2" ] , dtype=np.uint8)
                mask2= cv2.inRange (hsv, lower2 ,upper2 )
                mask = cv2.bitwise_or(mask, mask2)

            mask=cv2.morphologyEx ( mask, cv2.MORPH_OPEN , kernel,iterations =2)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)



            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                area=cv2.contourArea (cnt )
                obj_type = None

                if min_block_area<= area <=max_block_area:
                    obj_type = "block"
                elif min_mat_area<= area<= max_mat_area :
                    obj_type = "mat"
                else:
                    continue

                M = cv2.moments(cnt)
                if M["m00"] == 0 :
                    continue

                cx= float (M["m10" ] /M["m00"] )
                cy =float( M ["m01"] /M[ "m00"])
                bx , by ,bw , bh =cv2.boundingRect (cnt)

                obj_name = f"{color_name}_{obj_type}"
                detected_objects.append (DetectedObject (
                    name=obj_name,
                    color =color_name,
                    obj_type= obj_type,
                    pixel_x=cx,
                    pixel_y=cy,
                    area_px=float(area),
                    confidence=0.95,
                    bbox = (bx,by, bw, bh )
                ) )

        return detected_objects

    def draw_detections(self, image , detections : List [DetectedObject]) :
        if not CV2_AVAILABLE or image is None:

            return image
        annotated = image.copy()
        color_map ={
            "red":( 0,0, 255 ) ,
            "blue":(255 ,100,0 ) ,
            "green" :( 0 , 200,0 ) ,
            "yellow": ( 0, 230 , 255)
        }
        for det in detections :
            x , y,w, h=det.bbox
            box_col = color_map.get( det.color ,(255 , 255, 255 ))
            cv2.rectangle(annotated, (x, y), (x + w, y + h), box_col, 2)
            cv2.circle (annotated ,( int (det.pixel_x) ,int (det.pixel_y ) ), 4, ( 0,255 ,255) , - 1 )

            label= f"{det.name} ({det.world_x:.0f},{det.world_y:.0f}mm)"
            cv2.putText(annotated, label, (x, max(20, y - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX , 0.5,(255, 255 , 255),1, cv2.LINE_AA )
        return annotated
