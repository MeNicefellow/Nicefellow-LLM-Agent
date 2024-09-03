from utils import llm_chatter
import json
import requests

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
            return {
                "name": "Default Agent",
                "expertise": "General problem-solving",
                "traits": ["adaptive", "analytical", "persistent"]
            }

    def create_plan(self):
        prompt = f"""Create a detailed plan to achieve the following goal: {self.goal}.
        Provide the plan as a JSON array of step descriptions. For example:
        [
            "Research current market trends",
            "Analyze historical stock data",
            "Develop a prediction model",
            "Test the model with recent data",
            "Generate growth predictions"
        ]
        Provide only the JSON array in your response, with no additional text."""
        
        response = self.llm.communicate(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return ["Research the problem", "Analyze available data", "Develop a solution", "Test the solution", "Present results"]

    def next_action(self):
        if self.current_step < len(self.plan):
            step = self.plan[self.current_step]
            prompt = f"""For the following step in our plan: "{step}"
            Determine if this step requires Python code execution or a DuckDuckGo search.
            If it requires Python code, provide the exact code to execute.
            If it requires a search, provide the exact search query to use.
            Return your response as a JSON object with the following structure:
            {{
                "type": "python" or "search",
                "description": "Brief description of the action",
                "code": "Python code to execute" (only if type is "python"),
                "query": "Search query to use" (only if type is "search")
            }}
            Provide only the JSON object in your response, with no additional text."""
            
            response = self.llm.communicate(prompt)
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {"type": "search", "description": step, "query": f"{step} related to {self.goal}"}
        return None

    def execute_action(self, action):
        if action['type'] == 'python':
            # In a real-world scenario, you'd want to add more security measures here
            result = exec_python_code(action['code'])
        elif action['type'] == 'search':
            result = search_duckduckgo(action['query'])
        else:
            result = "Unknown action type"
        
        return result

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

def exec_python_code(code):
    # This is a simplified version. In a real-world scenario, you'd want to add more security measures
    try:
        exec_globals = {}
        exec(code, exec_globals)
        return str(exec_globals.get('result', 'Code executed successfully'))
    except Exception as e:
        return f"Error executing code: {str(e)}"

def search_duckduckgo(query):
    url = f"https://api.duckduckgo.com/?q={query}&format=json"
    response = requests.get(url)
    data = response.json()
    return data.get('Abstract', 'No results found')