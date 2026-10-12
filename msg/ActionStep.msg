# Atomic action step representing a single robot manipulation command
string action        # "pick", "place", "move_to", "open_gripper", "close_gripper"
string object_name   # Name of target object (e.g., "red_block"), or empty string
string target_name   # Name of placement target (e.g., "blue_mat"), or empty string
