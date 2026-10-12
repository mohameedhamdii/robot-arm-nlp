import os
import logging
from typing import List, Optional
from .colour_segmentation import DetectedObject

logger = logging.getLogger(__name__)

try :
    import cv2
    import numpy as np
    CV2_AVAILABLE =True
except ImportError:


    CV2_AVAILABLE=False
    cv2 = None
    np=None


class YOLODetector :

    def __init__ (self, model_path : Optional [ str] =None , conf_threshold:float= 0.5,nms_threshold :float = 0.4):
        self.model_path = model_path or os.path.join(os.path.dirname(__file__), "..", "..", "models", "yolov8n_blocks.onnx")
        self.conf_threshold=conf_threshold
        self.nms_threshold=nms_threshold
        self.classes = [
            "red_block","blue_block","green_block" ,"yellow_block" ,
            "red_mat","blue_mat","green_mat","yellow_mat"
        ]


        self.net = None
        self.load_model()

    def load_model(self) -> bool:
        if not CV2_AVAILABLE:
            return False
        if os.path.exists (self.model_path):

            try:
                self.net = cv2.dnn.readNetFromONNX(self.model_path)
                logger.info (f"Loaded YOLO ONNX model from {self.model_path}" )
                return True
            except Exception as e:
                logger.warning(f"Failed to load ONNX model: {e}" )
        return False

    def is_available ( self)-> bool:
        return self.net is not None


    def detect( self, image ) ->List[DetectedObject]:
        if not self.is_available() or image is None:
            return []

        h , w= image.shape[: 2 ]
        blob = cv2.dnn.blobFromImage(image, 1.0 / 255.0, (640, 640), swapRB=True, crop=False)
        self.net.setInput ( blob )
        preds = self.net.forward()

        detections :List[ DetectedObject] =[ ]
        if len(preds.shape ) == 3 :
            preds = np.squeeze(preds, axis=0).T

        boxes= [ ]
        confidences = []
        class_ids =[]

        for row in preds:
            scores =row[4 : ]
            class_id = np.argmax(scores)
            confidence =scores [ class_id]

            if confidence> self.conf_threshold:
                cx, cy, bw, bh = row[0], row[1], row[2], row[3]
                x =int ( (cx- ( bw / 2.0) )*(w/ 640.0 ) )

                y=int((cy-(bh / 2.0)) * (h/ 640.0 ))
                bw =int (bw* (w/640.0) )
                bh = int(bh * (h / 640.0))
                boxes.append([x, y, bw, bh])
                confidences.append ( float( confidence ) )
                class_ids.append (class_id)

        indices = cv2.dnn.NMSBoxes(boxes, confidences , self.conf_threshold ,self.nms_threshold )
        if len(indices )>0 :
            for idx in indices.flatten():
                bx , by, bw, bh=boxes [idx]
                cid = class_ids [ idx ]
                name = self.classes[cid] if cid < len(self.classes) else f"object_{cid}"
                color=name.split ( "_" ) [0 ]
                obj_type = name.split("_")[1] if "_" in name else "block"


                cx= float (bx + (bw/ 2.0))
                cy = float(by + (bh / 2.0))

                detections.append(DetectedObject(
                    name= name,
                    color= color ,
                    obj_type = obj_type,
                    pixel_x =cx ,
                    pixel_y= cy,
                    confidence =confidences [idx],
                    bbox =(bx , by ,bw,bh)
                ))

        return detections
