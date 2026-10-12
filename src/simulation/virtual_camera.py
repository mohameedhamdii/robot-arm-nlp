import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
try:
    from ..perception.calibrate import CameraCalibrator
except ( ImportError, ValueError ):
    from src.perception.calibrate import CameraCalibrator


class VirtualCamera :
    def __init__(self,width : int=640,height:int = 480):
        self.width = width


        self.height = height
        self.calibrator = CameraCalibrator ()

        self.objects ={
            "mats" : {
                "blue_mat": {"x": 60.0, "y": 180.0, "color_bgr": (230, 120, 20), "size_px": 80},
                "yellow_mat":{"x" :-70.0 ,"y" : 200.0,"color_bgr":(30,210,230) ,"size_px" :80},
                "green_mat":{"x" :70.0,"y" :90.0 ,"color_bgr":( 30 , 180,30 ),"size_px" :80 } ,
                "red_mat": {"x": -60.0, "y": 100.0, "color_bgr": (20, 20, 220), "size_px": 80}
            } ,
            "blocks":{
                "red_block": {"x": -50.0, "y": 140.0, "color_bgr": (20, 20, 220), "size_px": 28},
                "green_block": {"x": 40.0, "y": 110.0, "color_bgr": (30, 180, 30), "size_px": 28},
                "blue_block": {"x": -40.0, "y": 180.0, "color_bgr": (230, 120, 20), "size_px": 28},
                "yellow_block": {"x": 50.0, "y": 150.0, "color_bgr": (30, 210, 230), "size_px": 28}
            }
        }

    def move_block(self, block_name :str ,target_x: float , target_y : float ):

        if block_name in self.objects["blocks"]:
            self.objects["blocks"][block_name]["x"] = target_x
            self.objects[ "blocks"] [block_name ]["y" ] = target_y

    def render_frame (self , arm_tcp_xy :Optional[Tuple [float,float ] ] =None ) ->np.ndarray:
        img =np.full (( self.height ,self.width, 3 ) , 246, dtype=np.uint8)



        # light coordinate grid overlay
        cv2.rectangle ( img ,(20,20),(self.width - 20,self.height - 20), ( 220, 220, 220), 2)
        for gy in range(60, self.height - 40, 60 ) :
            cv2.line(img, (20, gy), (self.width - 20, gy), (235, 235, 235), 1)
        for gx in range(60, self.width - 40, 60):
            cv2.line (img, ( gx,20) , ( gx ,self.height -20) ,(235 , 235 ,235 ), 1)

        base_u, base_v = self.calibrator.world_to_pixel(0.0, 0.0, self.width, self.height)

        cv2.circle( img,( int ( base_u ) ,int( base_v ) ) ,16 ,( 80 ,80 , 80), -1)
        cv2.putText(img, "ARM BASE (0,0)", (int(base_u) - 55, int(base_v) - 22),
                    cv2.FONT_HERSHEY_SIMPLEX,0.45,( 60,60 , 60 ) ,1 )

        #target destination mats
        for mat_name, mat in self.objects[ "mats"].items ():
            u, v = self.calibrator.world_to_pixel(mat["x"], mat["y"], self.width, self.height)
            s= mat["size_px" ] // 2
            x1, y1 = int(u - s), int(v - s)
            x2,y2=int(u + s ),int (v + s )

            cv2.rectangle ( img ,(x1, y1 ) ,(x2 ,y2 ) , mat["color_bgr"],-1)

            cv2.rectangle (img , (x1, y1 ) ,(x2, y2) , ( 255 ,255,255) , 2 )

            label = mat_name.replace("_", " ").title()
            cv2.putText( img , label , ( x1+4,y2 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX , 0.35, (255, 255 ,255 ) , 1)

        #pickable blocks with subtle shadow
        for block_name, blk in self.objects["blocks"].items():
            u,v=self.calibrator.world_to_pixel (blk ["x" ] ,blk[ "y" ], self.width, self.height )
            s=blk[ "size_px" ] //2
            x1 , y1=int( u -s),int ( v-s )
            x2, y2 = int(u + s), int(v + s)

            cv2.rectangle(img, (x1 + 3, y1 + 3), (x2 + 3, y2 + 3), (180, 180, 180), -1)
            cv2.rectangle (img, (x1, y1), ( x2 ,y2 ) , blk[ "color_bgr"], -1 )
            cv2.rectangle (img,( x1,y1),(x2, y2 ),(0, 0, 0 ) ,1)

            cv2.circle( img , ( int ( u),int (v )),2 ,(255, 255 , 255),- 1)

        # crosshair marker on end-effector projection
        if arm_tcp_xy:
            tcp_x, tcp_y = arm_tcp_xy
            tu , tv =self.calibrator.world_to_pixel ( tcp_x ,tcp_y, self.width ,self.height )
            cv2.drawMarker (img , ( int( tu ) ,int(tv )), ( 0, 0 ,255) , cv2.MARKER_CROSS, 20 ,2 )

        return img

    def get_jpeg_bytes(self) -> bytes:
        frame= self.render_frame( )
        ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

        return buffer.tobytes ()if ret else b""
