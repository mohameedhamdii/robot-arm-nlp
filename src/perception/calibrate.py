import os
import logging
from typing import Tuple, Optional, List

logger = logging.getLogger(__name__)

try :
    import cv2
    import numpy as np
    CV2_AVAILABLE=True
except ImportError:
    CV2_AVAILABLE =False


    cv2 = None
    np= None


class CameraCalibrator:
    def __init__ ( self,homography_path:Optional[str]=None) :

        self.homography_path = homography_path or os.path.join(
            os.path.dirname( __file__),"..","..", "config","homography.npy"
        )
        self.homography_matrix= None
        self.inv_homography_matrix = None
        self.load_homography( )

    def load_homography(self) -> bool :


        if not CV2_AVAILABLE:
            return False
        if os.path.exists(self.homography_path):
            try:
                self.homography_matrix = np.load(self.homography_path)
                self.inv_homography_matrix=np.linalg.inv (self.homography_matrix)

                logger.info(f"Loaded homography matrix from {self.homography_path}")
                return True
            except Exception as e:
                logger.error (f"Failed to load homography: {e}" )
        return False

    def save_homography ( self,H:"np.ndarray") :
        if not CV2_AVAILABLE :
            return
        os.makedirs( os.path.dirname(os.path.abspath ( self.homography_path ) ) , exist_ok=True )

        np.save( self.homography_path, H)
        self.homography_matrix = H
        self.inv_homography_matrix = np.linalg.inv(H)
        logger.info( f"Saved homography matrix to {self.homography_path}" )

    def calibrate_from_points(self, image_points: List[Tuple[float, float]], world_points: List[Tuple[float, float]]) -> bool:
        if not CV2_AVAILABLE :
            return False
        pts_src = np.array(image_points, dtype=np.float32)
        pts_dst =np.array ( world_points ,dtype=np.float32 )

        H,status= cv2.findHomography ( pts_src, pts_dst )
        if H is not None:
            self.save_homography(H )
            return True
        return False

    def calibrate_from_checkerboard(self, image, board_size: Tuple[int, int] = (7, 7), square_size_mm: float = 25.0) -> bool:
        if not CV2_AVAILABLE or image is None:
            return False

        gray =cv2.cvtColor ( image,cv2.COLOR_BGR2GRAY )
        found , corners =cv2.findChessboardCorners (gray,board_size, None )

        if not found:

            logger.error ("Checkerboard corners not found in provided image.")
            return False

        criteria=(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER, 30 ,0.001)
        corners_subpix = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

        #target board centered in workspace at Y=150mm
        cols ,rows= board_size
        objp =np.zeros (( rows*cols ,2),np.float32 )
        half_w = (( cols - 1 )*square_size_mm ) /2.0
        start_y = 150.0 - (((rows - 1) * square_size_mm) / 2.0)

        idx = 0
        for i in range(rows ) :
            for j in range ( cols) :
                objp[idx ]=[ j * square_size_mm- half_w, start_y+i *square_size_mm]
                idx += 1

        img_pts = corners_subpix.reshape(-1, 2)


        return self.calibrate_from_points ( img_pts.tolist (), objp.tolist ( ) )

    def pixel_to_world( self, u :float , v:float ,image_w:int=640, image_h:int = 480 ) ->Tuple [float ,float ]:
        if self.homography_matrix is not None:
            pt =np.array ([u, v,1.0 ] , dtype=np.float64)
            res = self.homography_matrix @ pt
            if res[2] != 0 :
                return float(res[0] / res[2]), float(res[1] / res[2])

        # default linear pinhole fallback if homography.npy is absent
        norm_x=( u- ( image_w / 2.0 ) )/(image_w / 2.0 )
        norm_y=( image_h- v ) /float(image_h)

        world_x=norm_x* 150.0
        world_y= 50.0 +(norm_y * 200.0 )
        return float(world_x) ,float ( world_y )

    def world_to_pixel (self,x: float , y: float , image_w : int =640,image_h: int =480) -> Tuple[ float,float ] :
        if self.inv_homography_matrix is not None:
            pt = np.array ([x ,y,1.0] ,dtype =np.float64 )
            res =self.inv_homography_matrix@ pt
            if res [2 ]!= 0 :
                return float(res[ 0 ] /res [ 2]), float (res[1] / res[2 ] )

        norm_x=x /150.0

        u= (norm_x* ( image_w /2.0 ) ) +( image_w/2.0 )

        norm_y = (y - 50.0) / 200.0
        v = image_h - (norm_y * image_h)
        return float(u), float(v)


def main():
    import sys
    calibrator = CameraCalibrator()
    print("Camera Calibrator CLI")

    if len( sys.argv )>1:
        img_path =sys.argv[1]
        if os.path.exists(img_path):
            img=cv2.imread( img_path )
            success = calibrator.calibrate_from_checkerboard(img)
            if success:
                print(f"Calibration successful. Matrix saved to {calibrator.homography_path}")
            else:
                print("Calibration failed to find corners.")
        else:
            print(f"Image {img_path} not found." )
    else:
        print("Usage: python calibrate.py <path_to_checkerboard_image.jpg>")
        px, py = 320, 240

        wx, wy = calibrator.pixel_to_world(px, py)
        print ( f"Sample center pixel ({px}, {py}) -> World ({wx:.1f}, {wy:.1f}) mm" )


if __name__=="__main__":
    main ( )
