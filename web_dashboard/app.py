import os
import sys
import json
import asyncio
import logging
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse


from pydantic import BaseModel

sys.path.insert(0, os.path.abspath( os.path.join(os.path.dirname( __file__ ) ,"..") ))

from src.orchestrator.orchestrator_node import OrchestratorPipeline
from src.simulation.virtual_camera import VirtualCamera

from src.simulation.virtual_arm import VirtualArm
from src.motion.ik_solver import JointAngles

logging.basicConfig( level= logging.INFO )
logger =logging.getLogger("dashboard")

app= FastAPI (title ="Robot Arm NLP Dashboard", version = "1.0.0" )



orchestrator = OrchestratorPipeline(force_mock_hardware=True)
virtual_camera = VirtualCamera()
virtual_arm =VirtualArm ()
orchestrator.perception.latest_frame =virtual_camera.render_frame( )

active_websockets = set()


class CommandRequest ( BaseModel ):

    instruction : str


@app.get("/video_feed")
def video_feed ():
    def generate_frames( ):
        while True:
            frame = virtual_camera.render_frame()
            detections = orchestrator.perception.process_frame(frame)
            annotated = orchestrator.perception.segmenter.draw_detections(frame, detections)

            import cv2

            ret,buffer = cv2.imencode (".jpg" , annotated,[ cv2.IMWRITE_JPEG_QUALITY, 80] )
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' +buffer.tobytes( ) + b'\r\n' )
            import time
            time.sleep( 0.06)

    return StreamingResponse(generate_frames( ) , media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/api/telemetry")
def get_telemetry( ) :
    curr_angles = orchestrator.motion.driver.get_current_angles()
    virtual_arm.set_angles(curr_angles)
    return{
        "angles": curr_angles.to_dict(),
        "joints_3d": virtual_arm.get_joint_positions_3d (),
        "is_stopped": orchestrator.motion.is_stopped
    }


@ app.get ("/api/objects" )
def get_objects( ):
    detections = orchestrator.perception.cached_detections
    return[
        {
            "name": d.name,
            "type" :d.obj_type,
            "color":d.color ,
            "x" : round( d.world_x , 1 ),
            "y": round(d.world_y, 1),
            "z": round (d.world_z,1 ) ,
            "confidence" : round( d.confidence,2 )
        }
        for d in detections
    ]


@app.post("/api/command")
async def execute_command(req : CommandRequest ):
    async def run_pipeline () :
        def step_cb(angles :JointAngles) :
            virtual_arm.set_angles(angles)
            asyncio.run_coroutine_threadsafe(broadcast_telemetry(angles), loop)

        def progress_cb ( stage : str,msg : str ) :
            asyncio.run_coroutine_threadsafe( broadcast_log( stage ,msg ) ,loop)


        orig_callback =orchestrator.motion._telemetry_callback if hasattr(orchestrator.motion,"_telemetry_callback") else None
        
        def motion_step(angles ) :
            virtual_arm.set_angles(angles)
            #drag simulated block if gripper is clamped
            if angles.gripper >90.0 :
                fk_x, fk_y, fk_z= orchestrator.motion.ik.solve_fk( angles)
                for blk_name in list(virtual_camera.objects["blocks"].keys()):
                    bx=virtual_camera.objects ["blocks"] [ blk_name ]["x"]
                    by = virtual_camera.objects["blocks"][blk_name]["y"]
                    if abs(fk_x- bx ) <40 and abs( fk_y- by ) < 40 :
                        virtual_camera.move_block(blk_name, fk_x, fk_y)
                        break

            asyncio.run_coroutine_threadsafe (broadcast_telemetry(angles ) , loop)

        res= await asyncio.to_thread(
            orchestrator.execute_instruction ,
            req.instruction ,
            progress_callback =progress_cb
        )
        return res



    loop=asyncio.get_event_loop()
    asyncio.create_task(run_pipeline () )
    return {"status": "started" , "instruction":req.instruction}


@ app.post( "/api/estop" )
def emergency_stop ( ):
    orchestrator.motion.emergency_stop()
    return{ "status" : "stopped", "is_stopped" : True }


@ app.post ("/api/reset_estop")
def reset_estop():
    orchestrator.motion.reset_estop()
    return {"status": "resumed", "is_stopped": False}


async def broadcast_telemetry(angles: JointAngles):
    if not active_websockets:
        return
    virtual_arm.set_angles(angles)
    data=json.dumps ( {
        "type":"telemetry" ,
        "angles": angles.to_dict(),
        "joints_3d" :virtual_arm.get_joint_positions_3d ()
    })
    disconnected = set()
    for ws in active_websockets:
        try:
            await ws.send_text(data)
        except Exception :
            disconnected.add (ws )

    active_websockets.difference_update ( disconnected)


async def broadcast_log(stage: str, msg: str):
    if not active_websockets:
        return
    data = json.dumps({
        "type": "log",
        "stage":stage,
        "message" :msg
    } )
    disconnected = set()
    for ws in active_websockets:
        try:

            await ws.send_text ( data)
        except Exception:
            disconnected.add(ws)
    active_websockets.difference_update ( disconnected)


@app.websocket("/ws")
async def websocket_endpoint (websocket : WebSocket):
    await websocket.accept( )
    active_websockets.add ( websocket)
    curr = orchestrator.motion.driver.get_current_angles()
    virtual_arm.set_angles( curr )
    await websocket.send_text(json.dumps({
        "type":"telemetry",
        "angles": curr.to_dict (),
        "joints_3d" : virtual_arm.get_joint_positions_3d()
    } ))
    try:
        while True :

            await websocket.receive_text()
    except WebSocketDisconnect :
        active_websockets.remove(websocket)


static_dir = os.path.join( os.path.dirname ( __file__) ,"static")
if os.path.exists (static_dir ) :
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__=="__main__":
    import uvicorn
    uvicorn.run ("web_dashboard.app:app",host="0.0.0.0",port = 8000,reload=False )
