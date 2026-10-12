import os
import re
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
try:
    from .prompt_templates import SYSTEM_PROMPT ,build_user_prompt
except(ImportError ,ValueError ):
    from prompt_templates import SYSTEM_PROMPT,build_user_prompt



logger = logging.getLogger(__name__)


class BaseLLMBackend ( ABC ):
    @abstractmethod
    def plan (self, instruction: str , visible_objects:List[str] ) ->List [Dict[ str , Any ] ] :
        pass



class RuleBasedBackend(BaseLLMBackend):
    def plan(self ,instruction :str ,visible_objects: List [ str ]) -> List [Dict[str ,Any]] :
        logger.info ( f"Using RuleBasedBackend for instruction: '{instruction}'")
        text = instruction.lower().strip()
        actions = []



        colors= ["red" ,"blue" , "green","yellow" , "orange" , "purple"]
        
        # split conjunction clauses
        sub_clauses = re.split(r'\band\b|\bthen\b|;|,', text)
        
        for clause in sub_clauses:
            clause = clause.strip()
            if not clause:
                continue


            detected_pick =None
            detected_place = None

            # match "put/move X on/to Y"
            match_move = re.search(r'(?:(?:put|move|place|transfer|drop|set)\s+)?(?:the\s+)?([a-z0-9_\s]+?)\s+(?:on(?:to)?|to|in(?:to)?)\s+(?:the\s+)?([a-z0-9_\s]+)', clause)
            if match_move:
                obj_cand=match_move.group ( 1 ).strip().replace(" ","_")
                dest_cand= match_move.group (2).strip ( ).replace(" " , "_")
                
                # skip pronoun targets like "it", "that"
                if obj_cand.lower( )not in( "it","this","that" , "them" ):
                    detected_pick = self._match_to_visible ( obj_cand,visible_objects , preferred_type="block")

                detected_place = self._match_to_visible(dest_cand, visible_objects, preferred_type="mat")
            else:
                match_pick = re.search ( r'(?:pick(?:\s+up)?|grab|take|lift)\s+(?:the\s+)?([a-z0-9_\s]+)', clause)
                if match_pick:
                    obj_cand= match_pick.group(1 ).strip ( ).replace( " ", "_")
                    if obj_cand.lower() not in ("it", "this", "that", "them"):
                        detected_pick= self._match_to_visible(obj_cand , visible_objects , preferred_type ="block")

                match_place = re.search ( r'(?:place|put|drop|set)(?:\s+it)?\s+(?:on(?:to)?|to|at)\s+(?:the\s+)?([a-z0-9_\s]+)', clause)
                if match_place:
                    dest_cand = match_place.group( 1 ).strip().replace (" ","_")
                    detected_place = self._match_to_visible(dest_cand, visible_objects, preferred_type="mat")

            # heuristic color matching fallback
            if not detected_pick and not detected_place:
                for color in colors :
                    block_name=f"{color}_block"
                    mat_name = f"{color}_mat"
                    if ( f"{color} block" in clause or block_name in clause ) and "pick" in clause:
                        if block_name in visible_objects or not visible_objects :
                            detected_pick = block_name
                    elif( f"{color} mat" in clause or mat_name in clause) and( "place" in clause or "on" in clause or "to" in clause) :
                        if mat_name in visible_objects or not visible_objects:
                            detected_place=mat_name

            if detected_pick:

                actions.append({
                    "action" :"pick",
                    "object_name" : detected_pick ,
                    "target_name":None
                })
            if detected_place:
                actions.append({
                    "action": "place" ,
                    "object_name": None,
                    "target_name" :detected_place
                })

        return actions

    def _match_to_visible( self, candidate : str , visible_objects :List[str ] , preferred_type:str ="block" ) -> Optional[str]:
        candidate_clean = candidate.replace("the_", "").replace("_block", "").replace("_mat", "")
        for vis in visible_objects:
            if candidate==vis or candidate_clean ==vis :
                return vis
        
        colors =["red" , "blue" ,"green","yellow" ,"orange" , "purple" ]
        for color in colors :
            if color in candidate_clean:
                target_name=f"{color}_{preferred_type}"
                if target_name in visible_objects:


                    return target_name
                for vis in visible_objects :
                    if vis.startswith ( color) :
                        return vis
                return target_name
        
        for vis in visible_objects :
            if candidate_clean in vis :
                return vis
        return candidate if candidate else None


class LlamaCppBackend ( BaseLLMBackend ):
    def __init__(self, model_path :str, n_ctx :int =2048, n_threads :int = 4 ):
        self.model_path = model_path
        self.llm = None
        try:
            from llama_cpp import Llama
            if os.path.exists(model_path):
                logger.info(f"Loading GGUF model from {model_path}...")
                self.llm = Llama(
                    model_path= model_path,
                    n_ctx=n_ctx,
                    n_threads=n_threads,
                    verbose =False
                )
            else:
                logger.warning(f"GGUF model not found at {model_path}")
        except ImportError:

            logger.warning ("llama-cpp-python is not installed." )

    def plan(self, instruction: str, visible_objects: List[str]) -> List[Dict[str, Any]]:
        if self.llm is None :
            raise RuntimeError("LlamaCpp model is not initialized." )

        user_content =build_user_prompt (instruction , visible_objects)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]

        response=self.llm.create_chat_completion (
            messages = messages,
            temperature = 0.0,
            max_tokens=512
        )
        content = response["choices"][0]["message"]["content"].strip()

        return self._clean_and_parse_json ( content)

    def _clean_and_parse_json(self, content: str) -> List[Dict[str, Any]]:
        cleaned=re.sub( r'```(?:json)?' ,'', content ).strip('` \n\r' )
        start_idx=cleaned.find ('[')
        end_idx = cleaned.rfind(']')
        if start_idx != - 1 and end_idx!= - 1 and end_idx >start_idx :
            cleaned = cleaned[start_idx:end_idx + 1]
        return json.loads(cleaned )


class LLMBackend:
    def __init__ ( self,model_path: Optional[str]=None):
        self.model_path = model_path or os.environ.get("ROBOT_ARM_LLM_PATH","models/phi-3-mini-4k-instruct.Q4_K_M.gguf" )

        self.llama_backend= None
        self.rule_backend = RuleBasedBackend()

        if os.path.exists ( self.model_path):
            try:
                self.llama_backend = LlamaCppBackend ( self.model_path )
            except Exception as e :
                logger.warning(f"Could not load LlamaCppBackend: {e}")

    def plan (self ,instruction:str ,visible_objects:List [ str ])->List [Dict[str , Any ]] :
        if self.llama_backend and self.llama_backend.llm :
            try :
                plan_result = self.llama_backend.plan(instruction, visible_objects)


                if isinstance(plan_result , list) and len (plan_result ) > 0:

                    return plan_result
            except Exception as e :
                logger.warning(f"LlamaCpp planning failed, falling back to rule-based: {e}")

        return self.rule_backend.plan ( instruction,visible_objects)
