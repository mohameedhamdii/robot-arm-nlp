import sys
import time
import logging
from typing import Optional
try:
    from .voice_capture import VoiceCapture
except (ImportError, ValueError):
    from voice_capture import VoiceCapture

logging.basicConfig (level=logging.INFO,format= "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s" )
logger=logging.getLogger ( "input_handler" )



try :
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String

    ROS2_AVAILABLE =True
except ImportError:
    ROS2_AVAILABLE =False
    Node = object
    String=None


class InputHandlerNode(Node):


    def __init__( self,mode :str = "text"):
        if ROS2_AVAILABLE:
            super().__init__("input_handler_node")
            self.publisher_=self.create_publisher(String,"/user_command", 10)
            self.get_logger ().info(f"InputHandlerNode initialized in [{mode}] mode.")
        else:
            logger.info(f"InputHandler initialized (standalone mode, ROS 2 not detected) in [{mode}] mode.")


        self.mode = mode
        self.voice_capture = VoiceCapture()

    def publish_command(self ,text:str )-> bool:
        clean_text = text.strip()
        if not clean_text:
            return False

        if ROS2_AVAILABLE and hasattr(self , "publisher_" ):
            msg= String()

            msg.data =clean_text
            self.publisher_.publish ( msg )
            self.get_logger().info(f"Published to /user_command: '{clean_text}'")
        else:
            logger.info(f"[Topic: /user_command] Published: '{clean_text}'")
        return True

    def run_text_loop ( self) :
        print("NLP Robot Arm input prompt. Type command or 'exit' to quit.")

        while True:
            try:
                user_input= input ( "robot> " ).strip ( )
                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit", "q"):
                    break
                self.publish_command( user_input)
            except (KeyboardInterrupt, EOFError):
                break

    def run_voice_loop (self ):
        print( "NLP Robot Arm voice mode. Speak prompt when ready (Ctrl+C to stop)." )

        while True :
            try:

                transcription =self.voice_capture.listen_and_transcribe ( duration =5)
                if transcription:
                    print(f"Heard: \"{transcription}\"")
                    self.publish_command (transcription)
                else:
                    print ( "(no speech detected, retrying)" )
                time.sleep(0.5)
            except KeyboardInterrupt:
                break


def main( args =None) :
    mode= "text"
    if len( sys.argv )>1 and "--voice" in sys.argv :
        mode = "voice"

    if ROS2_AVAILABLE:
        rclpy.init (args =args)
        node=InputHandlerNode ( mode =mode)


        try:
            if mode=="voice":
                node.run_voice_loop()
            else:
                node.run_text_loop()
        finally:
            node.destroy_node( )
            rclpy.shutdown ()
    else:
        node = InputHandlerNode(mode = mode)
        if mode =="voice" :
            node.run_voice_loop()
        else :
            node.run_text_loop()


if __name__=="__main__" :
    main ( )
