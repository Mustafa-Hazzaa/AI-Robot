from ollama import Client
from pydantic import BaseModel, Field
from typing import Literal, Optional, List
import json

class Config:
    FRONT_SAFE_THRESHOLD = 0.05
    TURN_90_DURATION = 2.0
    MODEL_NAME = "llama3.1:8b"
    TEMPERATURE = 0.5


class ActionDecision(BaseModel):
    action: Literal['forward', 'backward', 'left', 'right', 'stop']
    duration: Optional[float] = None
    distance: Optional[float] = None
    notes: Optional[str] = None


class ActionPlan(BaseModel):
    plan: List[ActionDecision]


class AIPlanner:
    """Encapsulates all AI (LLM) interactions."""
    def __init__(self, model_name=Config.MODEL_NAME, temperature=Config.TEMPERATURE):
        self.client = Client()
        self.model_name = model_name
        self.temperature = temperature

    def _get_system_prompt(self, schema: dict) -> str:
        return f"""
You are an Autonomous Director of Robot Choreography.
Translate ANY command into a creative plan of robot movements.
End every sequence with a 'stop' action.
Schema:
{json.dumps(schema, indent=2)}
"""

    def generate_plan(self, speech_command: str, distances: dict):
        """Main AI interaction."""
        schema = ActionPlan.model_json_schema()
        system_prompt = self._get_system_prompt(schema)

        response = self.client.chat(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Command: \"{speech_command}\" Generate a JSON plan."}
            ],
            format="json",
            options={"temperature": self.temperature}
        )

        raw_text = response['message']['content']
        parsed_data = json.loads(raw_text)
        plan = ActionPlan(**parsed_data)

        # Safety overrides + defaults
        final_plan = []
        DEFAULT_DISTANCE = 0.5
        DEFAULT_DURATION = 1.0

        front_distance = distances.get("front", 100.0)

        if front_distance < Config.FRONT_SAFE_THRESHOLD and plan.plan and plan.plan[0].action == 'forward':
            final_plan.append(ActionDecision(action="stop", notes="Safety override: obstacle detected").model_dump())
        else:
            for step in plan.plan:
                data = step.model_dump(exclude_none=True)
                if step.action in ['forward', 'backward', 'left', 'right']:
                    if 'distance' not in data and 'duration' not in data:
                        if step.action in ['left', 'right']:
                            data['duration'] = DEFAULT_DURATION
                        else:
                            data['distance'] = DEFAULT_DISTANCE
                final_plan.append(data)

        return final_plan
