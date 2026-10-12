#!/usr/bin/env python3
import os
import sys
import time
import argparse
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_i2c():
    print ( "\n--- 1. Testing I2C Bus & PCA9685 Detection ---" )
    try :


        import subprocess
        res= subprocess.run( [ "i2cdetect","-y", "1"], capture_output= True ,text=True)
        print(res.stdout)
        if "40" in res.stdout:

            print("[OK] PCA9685 detected at address 0x40.")
            return True
        else :
            print( "[WARN] Address 0x40 not found on I2C bus 1. Check SDA/SCL wiring and logic power (VCC).")
            return False
    except FileNotFoundError:
        print("[INFO] 'i2cdetect' tool not found (running on non-Linux or without i2c-tools).")


        return False


def test_camera() :
    print("\n--- 2. Testing Camera Module ---")
    try:
        from picamera2 import Picamera2
        picam2=Picamera2 ()

        config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"})
        picam2.configure(config)
        picam2.start()
        time.sleep(1.0)
        frame =picam2.capture_array()
        picam2.stop()
        picam2.close()
        print ( f"[OK] Picamera2 captured frame with shape {frame.shape}." )

        import cv2
        cv2.imwrite("camera_test.jpg" ,cv2.cvtColor( frame, cv2.COLOR_RGB2BGR ) )
        print("Saved test snapshot to camera_test.jpg")
        return True
    except Exception as e:
        print( f"[INFO] Picamera2 not available: {e}" )

    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened( ):
            ret, frame = cap.read()
            cap.release( )
            if ret and frame is not None:
                print ( f"[OK] OpenCV VideoCapture(0) captured frame with shape {frame.shape}." )
                cv2.imwrite ( "camera_test.jpg",frame )
                print("Saved test snapshot to camera_test.jpg")
                return True
        print( "[WARN] Could not capture from OpenCV VideoCapture(0). Check camera connection.")
        return False
    except Exception as e:
        print (f"[ERROR] Camera capture failed: {e}")
        return False



def test_servos ( target_joint = None) :
    print ( "\n--- 3. Testing PCA9685 Servo Movement ---")
    try:
        from adafruit_servokit import ServoKit
        kit=ServoKit (channels=16 , address =0x40 )
        print ("[OK] Connected to PCA9685 via CircuitPython ServoKit.")
    except Exception as e:
        print (f"[ERROR] Cannot connect to physical PCA9685: {e}" )
        print( "Ensure you are running on Raspberry Pi with I2C enabled and servo 6V power rail ON." )
        return False

    with open("config/servo_calibration.yaml" , "r" ) as f:
        cfg = yaml.safe_load(f).get("servos", {})

    joints_to_test = [target_joint] if target_joint else list(cfg.keys())

    for name in joints_to_test :
        if name not in cfg:


            print(f"Unknown joint: {name}")
            continue

        jcfg = cfg [name]
        ch = jcfg["channel"]
        min_us=jcfg.get("min_pulse_us",500 )
        max_us =jcfg.get( "max_pulse_us" ,2500)
        kit.servo[ch].set_pulse_width_range(min_us, max_us)

        print ( f"\nTesting Joint [{name}] on Channel {ch}:")
        print("  Moving to 90 deg (Center)...")
        kit.servo [ch ].angle=90
        time.sleep(1.0)

        print ("  Gentle wiggle: 80 -> 100 -> 90...")
        kit.servo[ch ].angle = 80
        time.sleep( 0.5 )
        kit.servo [ ch].angle= 100
        time.sleep (0.5)
        kit.servo[ ch ].angle = 90
        time.sleep( 0.5)
        print( f"  Joint [{name}] check complete.")


    print( "\n[OK] All tested servos responded." )
    return True


def main () :
    parser= argparse.ArgumentParser(description ="Robot Arm Hardware Smoke Tests")
    parser.add_argument ( "--all" , action ="store_true", help = "Run all hardware tests" )
    parser.add_argument( "--i2c", action ="store_true" , help="Test I2C bus detection" )
    parser.add_argument("--camera", action="store_true", help="Test camera image capture")
    parser.add_argument("--servos", action="store_true", help="Test servo movement")

    parser.add_argument("--joint", type=str, help="Test a single servo joint")

    args = parser.parse_args()

    if not any([args.all, args.i2c, args.camera, args.servos, args.joint]):
        parser.print_help()
        sys.exit(0)

    if args.all or args.i2c:
        test_i2c()
    if args.all or args.camera:
        test_camera()
    if args.all or args.servos or args.joint:
        test_servos(target_joint=args.joint)



if __name__== "__main__":
    main()
