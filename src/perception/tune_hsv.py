import os
import sys
import yaml
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np


    CV2_AVAILABLE= True
except ImportError :
    CV2_AVAILABLE=False
    cv2 = None
    np = None



def nothing ( x ):
    pass


class HSVTuner :
    def __init__( self ,config_path:Optional [str] =None ) :
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__),"..","..","config", "colour_ranges.yaml"
        )


        self.window_name= "HSV Calibration Tool"

    def run(self, camera_index: int = 0):
        if not CV2_AVAILABLE:
            print("OpenCV is required to run the HSV tuner GUI.")
            return

        print("Press 's' to save current range, 'q' to quit.")


        cv2.namedWindow(self.window_name)

        # trackbar setup
        cv2.createTrackbar("H_min", self.window_name, 0, 180, nothing)
        cv2.createTrackbar("H_max", self.window_name, 180, 180, nothing)
        cv2.createTrackbar("S_min" ,self.window_name,100 ,255 ,nothing)
        cv2.createTrackbar("S_max", self.window_name, 255, 255, nothing)
        cv2.createTrackbar("V_min", self.window_name, 100, 255, nothing)
        cv2.createTrackbar( "V_max" , self.window_name,255 ,255, nothing)

        cap = cv2.VideoCapture (camera_index)

        if not cap.isOpened():
            print ( f"Cannot open camera index {camera_index}. Creating test color gradient canvas.")
            frame =np.zeros( ( 480 , 640 , 3), dtype= np.uint8)
            for x in range(640):
                h = int((x / 640.0) * 180)
                frame [:, x ] = [h , 200 ,200]
            frame = cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)
        else:
            frame = None

        while True :
            if cap.isOpened():
                ret, img = cap.read()
                if not ret :
                    break
            else:
                img = frame.copy( )

            h_min =cv2.getTrackbarPos( "H_min", self.window_name)
            h_max = cv2.getTrackbarPos("H_max" , self.window_name )
            s_min = cv2.getTrackbarPos("S_min", self.window_name)
            s_max =cv2.getTrackbarPos ("S_max",self.window_name)
            v_min = cv2.getTrackbarPos ("V_min",self.window_name)
            v_max = cv2.getTrackbarPos("V_max", self.window_name)


            hsv=cv2.cvtColor(img , cv2.COLOR_BGR2HSV)
            lower= np.array ([h_min , s_min, v_min] ,dtype= np.uint8)
            upper=np.array( [ h_max ,s_max , v_max ] ,dtype= np.uint8 )

            mask = cv2.inRange(hsv, lower, upper)
            res = cv2.bitwise_and(img, img, mask=mask)

            combined=np.hstack( [ img , res] )
            cv2.imshow(self.window_name ,combined)

            key = cv2.waitKey (30 )& 0xFF
            if key==ord ('q') :
                break
            elif key == ord('s'):
                color = input ( "Enter color name to save (red/blue/green/yellow): ").strip( ).lower ( )
                self.save_color (color ,[ h_min ,s_min , v_min], [h_max,s_max,v_max] )

        if cap.isOpened():
            cap.release()


        cv2.destroyAllWindows()

    def save_color ( self , color_name: str, lower: list, upper: list):
        if not os.path.exists(self.config_path):
            data= {"colours": { } ,"detection":{}}
        else:
            with open ( self.config_path ,"r") as f:
                data = yaml.safe_load ( f ) or{}

        if "colours" not in data:
            data [ "colours" ]={ }

        data[ "colours" ] [color_name]={
            "hsv_lower":lower,
            "hsv_upper" :upper
        }

        with open ( self.config_path,"w" ) as f :
            yaml.safe_dump(data, f, default_flow_style = False )
        print(f"Saved {color_name} range {lower} - {upper} to {self.config_path}")


if __name__== "__main__" :
    tuner = HSVTuner()
    cam = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    tuner.run(camera_index=cam)
