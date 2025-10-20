# ----- AI Client -----
from ollama import Client
from pydantic import BaseModel, Field
from typing import Literal, Optional, List
import json

class Config:
    FRONT_SAFE_THRESHOLD = 0.05
    TURN_90_DURATION = 2.0
    MODEL_NAME = "qwen2.5vl"
    TEMPERATURE = 0.5   # lowered for consistency (less randomness)


class ActionDecision(BaseModel):
    """Defines a single robot movement step."""
    action: Literal['forward', 'backward', 'left', 'right', 'stop'] = Field(
        description="The movement command. Use 'left' or 'right' for turns."
    )
    duration: Optional[float] = Field(
        default=None,
        description="Duration in seconds. Use for turns or time-based movements."
    )
    distance: Optional[float] = Field(
        default=None,
        description="Distance in meters for forward/backward motions."
    )
    notes: Optional[str] = Field(
        default=None,
        description="Brief description of the action."
    )


class ActionPlan(BaseModel):
    """Top-level structure containing the plan list."""
    plan: List[ActionDecision] = Field(
        description="A sequence of robot actions. The final action MUST be 'stop'."
    )


class AIPlanner:
    def __init__(self, model_name=Config.MODEL_NAME, temperature=Config.TEMPERATURE):
        self.client = Client()
        self.model_name = model_name
        self.temperature = temperature

    def generate_plan(self, speech_command: str, distances: dict):
        schema = ActionPlan.model_json_schema()

        # --- SYSTEM PROMPT (identical logic to first program) ---
        system_prompt = f"""
You are an Autonomous Director of Robot Choreography. Your job is to translate ANY user command into a precise, logical sequence of robot actions.
Your final output MUST STRICTLY conform to the provided JSON schema.

EXECUTION RULES:
1. Output MUST be a JSON object with a top-level key "plan" (not just a list).
2. The "plan" array must include step-by-step robot actions.
3. The LAST action in the plan MUST always be 'stop'.
4. When drawing geometric shapes (square, triangle, etc.), use consistent turns (e.g., always 'right' for a clockwise square).
5. Use realistic numeric values: forward distances in meters, turns via 'duration' seconds for 90° angles.
6. IN GEOMETRY(Square,triangle,hexagon ,etc) :Avoid creativity or randomness — focus on consistent logic .

7- use creativity for abstract commands like dance etc

JSON SCHEMA:
{json.dumps(schema, indent=2)}
"""

        # --- USER PROMPT (match first program phrasing) ---
        user_prompt = f"""
Command: "{speech_command}"
Ultrasonic readings: {json.dumps(distances)}
Generate the complete JSON response that contains the top-level 'plan' array now.
"""

        # --- LLM CALL ---
        response = self.client.chat(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            format="json",
            options={"temperature": self.temperature}
        )

        raw_text = response['message']['content']
        print("\n🧠 Raw AI response:", raw_text)

        # --- JSON PARSING ---
        try:
            parsed_data = json.loads(raw_text)
            if "plan" not in parsed_data:
                raise ValueError("Missing top-level 'plan' key")
            plan = ActionPlan(**parsed_data)
        except Exception as e:
            print(f"❌ AI output parsing failed: {e}")
            plan = ActionPlan(plan=[
                ActionDecision(action="stop", notes=f"Fallback due to invalid AI output: {e}")
            ])

        # --- SAFETY LAYER (identical to first program) ---
        front_distance = distances.get("front", 100.0)
        final_plan = []
        DEFAULT_DISTANCE = 0.5
        DEFAULT_DURATION = 1.0

        if front_distance < Config.FRONT_SAFE_THRESHOLD:
            final_plan.append(ActionDecision(
                action="stop",
                notes="CRITICAL SAFETY OVERRIDE: Front distance too close."
            ).model_dump(exclude_none=True))
        else:
            for d in plan.plan:
                step = d.model_dump(exclude_none=True)
                if step["action"] in ["forward", "backward", "left", "right"]:
                    if "distance" not in step and "duration" not in step:
                        if step["action"] in ["left", "right"]:
                            step["duration"] = DEFAULT_DURATION
                            step["notes"] = step.get("notes", "") + " [DURATION DEFAULT INJECTED for turn]"
                        else:
                            step["distance"] = DEFAULT_DISTANCE
                            step["notes"] = step.get("notes", "") + " [DISTANCE DEFAULT INJECTED]"
                final_plan.append(step)

        return final_plan
