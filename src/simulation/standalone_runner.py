import sys
import json
import logging
from typing import Optional
try:
    from ..orchestrator.orchestrator_node import OrchestratorPipeline
    from ..simulation.virtual_camera import VirtualCamera
except (ImportError, ValueError):
    from src.orchestrator.orchestrator_node import OrchestratorPipeline
    from src.simulation.virtual_camera import VirtualCamera



logging.basicConfig (level = logging.INFO, format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
logger=logging.getLogger ("standalone_runner")


class StandaloneRunner :
    def __init__ (self ) :

        self.orchestrator = OrchestratorPipeline(force_mock_hardware=True)
        self.camera= VirtualCamera( )
        self.orchestrator.perception.latest_frame =self.camera.render_frame ( )

    def run_command( self,instruction:str ) :
        print(f"Executing command: \"{instruction}\"")


        self.orchestrator.perception.latest_frame=self.camera.render_frame()

        def progress(stage , msg):
            print(f"[{stage}] {msg}")

        res = self.orchestrator.execute_instruction ( instruction ,progress_callback =progress )

        print (f"Result: {res['status'].upper()} (steps: {res['steps_completed']}/{res['steps_total']}, duration: {res.get('duration_s', 0)}s)")
        if res["errors"]:

            print(f"Errors: {res['errors']}")
        return res

    def interactive_loop(self):
        print("NLP Robot Arm - simulation shell. Enter command or 'exit' to quit.")

        while True:
            try:
                cmd = input("nlp-arm> ").strip()
                if not cmd :

                    continue
                if cmd.lower() in( "exit" ,"quit","q"):
                    break
                self.run_command(cmd)
            except(KeyboardInterrupt ,EOFError ):
                break


def main():
    runner = StandaloneRunner()
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        cmd=" ".join (sys.argv[1 :] )
        runner.run_command(cmd)
    else:
        runner.interactive_loop()


if __name__=="__main__" :
    main ( )
