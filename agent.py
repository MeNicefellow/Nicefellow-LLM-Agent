from utils import llm_chatter
import json

class Agent:
    def __init__(self, goal):
        self.llm = llm_chatter()
        self.goal = goal
        self.profile = self.create_profile()
        self.memory = []
        self.plan = self.create_plan()
        self.current_step = 0

    def create_profile(self):
        prompt = f"""Create a profile for an AI agent with the goal: {self.goal}. Include name, expertise, and key traits.
        Return the profile as a JSON object with the following structure:
        {{
            "name": "Agent name",
            "expertise": "Agent's area of expertise",
            "traits": ["trait1", "trait2", "trait3"]
        }}
        Provide only the JSON object in your response, with no additional text."""
        
        response = self.llm.communicate(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # If JSON parsing fails, return a default profile
            return {
                "name": "Default Agent",
                "expertise": "General problem-solving",
                "traits": ["adaptive", "analytical", "persistent"]
            }

    def create_plan(self):
        prompt = f"""Create a detailed plan to achieve the following goal: {self.goal}.
        Provide a list of steps as a JSON array. For example:
        ["Step 1: Analyze the problem", "Step 2: Research possible solutions", "Step 3: Implement the best solution"]
        Provide only the JSON array in your response, with no additional text."""
        
        response = self.llm.communicate(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # If JSON parsing fails, return a default plan
            return ["Analyze the goal", "Research solutions", "Implement the best solution"]

    def next_action(self):
        if self.current_step < len(self.plan):
            return self.plan[self.current_step]
        return None

    def execute_action(self, action):
        # Implement action execution logic here
        # For now, we'll just return a placeholder result
        return f"Executed action: {action}"

    def update_memory(self, action, result):
        self.memory.append({"action": action, "result": result})

    def to_dict(self):
        return {
            "goal": self.goal,
            "profile": self.profile,
            "memory": self.memory,
            "plan": self.plan,
            "current_step": self.current_step
        }