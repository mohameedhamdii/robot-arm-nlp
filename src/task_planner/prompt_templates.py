from typing import List

SYSTEM_PROMPT= """You are a robot arm task planner. You receive:
1. A natural-language instruction from the user.
2. A list of objects currently visible on the workspace with their names.

Your job is to output a JSON array of atomic steps the robot must execute. Each step is a JSON object:
{
  "action": "pick" | "place",
  "object_name": "<name of object to pick, e.g. 'red_block'>",
  "target_name": "<name of destination, e.g. 'blue_mat'>"
}

Rules:
- Only use object and target names from the provided visible objects list.
- "pick" requires "object_name" to be set and "target_name" to be null.
- "place" requires "target_name" to be set and "object_name" to be null.
- A "place" must always follow a "pick".
- If the instruction is ambiguous or impossible, output: {"error": "<reason>"}.
- Output ONLY valid JSON. No explanation, no markdown, no extra text."""

FEW_SHOT_EXAMPLES=[
    {
        "visible_objects": ["red_block", "blue_block", "green_block", "red_mat", "blue_mat", "green_mat"],
        "instruction" : "Put the red block on the blue mat and the green block on the red mat",
        "output" : [
            {"action": "pick", "object_name": "red_block", "target_name": None},
            { "action": "place" , "object_name":None, "target_name": "blue_mat" },
            { "action":"pick","object_name": "green_block","target_name" : None} ,
            {"action": "place", "object_name": None, "target_name": "red_mat"}
        ]
    },
    {
        "visible_objects": ["yellow_block", "green_mat"],
        "instruction" :"Move the yellow block to the green mat" ,
        "output": [
            { "action": "pick" ,"object_name" :"yellow_block","target_name": None },
            {"action": "place", "object_name": None, "target_name": "green_mat"}
        ]
    }
]


def build_user_prompt(instruction:str, visible_objects :List[ str ] ) -> str:
    objects_str =", ".join ( visible_objects)if visible_objects else "none"
    return f"Visible objects: {objects_str}\n\nUser instruction: \"{instruction}\""
