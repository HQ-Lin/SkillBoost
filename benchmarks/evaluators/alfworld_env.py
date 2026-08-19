from __future__ import annotations

import os
import re
from typing import List, Tuple

                                                                            
TASKS = [
    "pick_and_place",
    "pick_two_obj_and_place",
    "look_at_obj_in_light",
    "pick_heat_then_place_in_recep",
    "pick_cool_then_place_in_recep",
    "pick_clean_then_place_in_recep",
]

def get_task_type(gamefile: str) -> str:
    for task in TASKS:
        if task in (gamefile or ""):
            return task
    return "other"

                                                                  
def _alfworld_data() -> str:
    data = os.environ.get("ALFWORLD_DATA") or os.path.expanduser("~/.cache/alfworld")
    return data

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alfworld_config.yaml")

def _expandvars(o):
    if isinstance(o, dict):
        return {k: _expandvars(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_expandvars(v) for v in o]
    if isinstance(o, str):
        return os.path.expandvars(o)
    return o

def build_config() -> dict:
    """load ALFWorld  (reference config_tw.yaml),  and  $ALFWORLD_DATA. """
    import yaml

    os.environ.setdefault("ALFWORLD_DATA", _alfworld_data())
    with open(_CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    return _expandvars(config)

def _infer_train_eval(gamefile: str) -> str:
    p = str(gamefile or "")
    if "/valid_seen/" in p:
        return "eval_in_distribution"
    if "/valid_unseen/" in p:
        return "eval_out_of_distribution"
    return "train"

                                                                      
def alfworld_projection(action_raw: str) -> Tuple[str, int]:
    """from modelraw outputextract. returned  (cleaned_action, valid).

    require same with  <think>  and  <action> label,  and not with  in .
    """
    original = action_raw or ""
    text = original.lower()
    start_tag, end_tag = "<action>", "</action>"
    s, e = text.find(start_tag), text.find(end_tag)
    valid = 0
    if s != -1 and e != -1 and e > s:
        action = text[s + len(start_tag):e].strip()
        valid = 1
    else:
        action = text[-30:]
    if original.find("<think>") == -1 or original.find("</think>") == -1:
        valid = 0
    if re.search(r"[\u4e00-\u9fff]", original):
        valid = 0
    return action, valid

                                                                      
TEMPLATE_NO_HIS = (
    "\nYou are an expert agent operating in the ALFRED Embodied Environment.\n"
    "Your current observation is: {current_observation}\n"
    "Your admissible actions of the current situation are: [{admissible_actions}].\n\n"
    "Now it's your turn to take an action.\n"
    "You should first reason step-by-step about the current situation. This reasoning "
    "process MUST be enclosed within <think> </think> tags.\n"
    "Once you've finished your reasoning, you should choose an admissible action for "
    "current step and present it within <action> </action> tags.\n"
)

TEMPLATE_WITH_HIS = (
    "\nYou are an expert agent operating in the ALFRED Embodied Environment. "
    "Your task is to: {task_description}\n"
    "Prior to this step, you have already taken {step_count} step(s). Below are the most "
    "recent {history_length} observations and the corresponding actions you took: "
    "{action_history}\n"
    "You are now at step {current_step} and your current observation is: "
    "{current_observation}\n"
    "Your admissible actions of the current situation are: [{admissible_actions}].\n\n"
    "Now it's your turn to take an action.\n"
    "You should first reason step-by-step about the current situation. This reasoning "
    "process MUST be enclosed within <think> </think> tags.\n"
    "Once you've finished your reasoning, you should choose an admissible action for "
    "current step and present it within <action> </action> tags.\n"
)

class ObsBuilder:
    """buildinjecthistory test text, aligned with the reference AlfWorldEnvironmentManager."""

    def __init__(self, history_length: int = 2):
        self.history_length = history_length
        self.task = ""
        self.history: List[dict] = []                   

    def set_task(self, raw_obs: str) -> None:
        marker = "Your task is to: "
        idx = raw_obs.find(marker)
        self.task = raw_obs[idx + len(marker):].strip() if idx != -1 else ""

    @staticmethod
    def _fmt_admissible(admissible: List[str]) -> str:
        return "\n ".join(f"'{s}'" for s in admissible if s != "help")

    def build(self, raw_obs: str, admissible: List[str], init: bool) -> str:
        adm = self._fmt_admissible(admissible)
        if init or self.history_length <= 0:
            return TEMPLATE_NO_HIS.format(current_observation=raw_obs, admissible_actions=adm)
        recent = self.history[-self.history_length:]
        start_idx = len(self.history) - len(recent)
        lines = []
        for j, rec in enumerate(recent):
            step_num = start_idx + j + 1
            lines.append(
                f"[Observation {step_num}: '{rec['obs']}', Action {step_num}: '{rec['action']}']"
            )
        action_history = "\n".join(lines)
        return TEMPLATE_WITH_HIS.format(
            task_description=self.task,
            step_count=len(self.history),
            history_length=len(recent),
            action_history=action_history,
            current_step=len(self.history) + 1,
            current_observation=raw_obs,
            admissible_actions=adm,
        )

    def record(self, prev_obs: str, action: str) -> None:
        self.history.append({"obs": prev_obs, "action": action})

                                                                          
class AlfredSingleEnv:
    """ as single  gamefile build one  ALFWorld text. """

    def __init__(self, gamefile: str, seed: int = 42):
        from alfworld.agents.environment import get_environment

        config = build_config()
        train_eval = _infer_train_eval(gamefile)
        env_type = config["env"]["type"]
        base = get_environment(env_type)(config, train_eval=train_eval)
        base.game_files = [gamefile]
        if hasattr(base, "num_games"):
            base.num_games = 1
        self.env = base.init_env(batch_size=1)
        self.env.seed(seed)
        self.gamefile = gamefile

    def reset(self) -> Tuple[str, List[str]]:
        obs, infos = self.env.reset()
        return obs[0], list(infos["admissible_commands"][0])

    def step(self, action: str) -> Tuple[str, List[str], bool, bool]:
        obs, scores, dones, infos = self.env.step([action])
        return (
            obs[0],
            list(infos["admissible_commands"][0]),
            bool(dones[0]),
            bool(infos["won"][0]),
        )
