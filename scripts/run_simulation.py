#!/usr/bin/env python3
import os
import sys
import argparse

# add repo root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.simulation.standalone_runner import StandaloneRunner


def main():
    parser =argparse.ArgumentParser( description ="Robot Arm NLP Simulator and Dashboard Runner" )
    parser.add_argument ( "--command", "-c" , type=str, help= "Execute a single natural language instruction" )
    parser.add_argument( "--dashboard","-d",action= "store_true",help = "Launch interactive Web Dashboard & visualizer")


    parser.add_argument ( "--port", "-p", type =int , default= 8000,help="Web dashboard port (default: 8000)" )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Web dashboard host (default: 0.0.0.0)")

    args =parser.parse_args()

    if args.dashboard:

        print(f"Starting dashboard at http://localhost:{args.port}" )
        import uvicorn
        uvicorn.run("web_dashboard.app:app", host=args.host, port=args.port, reload=False)
    elif args.command :
        runner=StandaloneRunner ( )
        runner.run_command(args.command)
    else :


        runner = StandaloneRunner( )
        runner.interactive_loop()


if __name__ == "__main__":
    main()
