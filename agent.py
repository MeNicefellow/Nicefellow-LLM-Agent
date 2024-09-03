from utils import llm_chatter
from llm_backends import get_llm_backend
import json
import sys
from duckduckgo_search import DDGS

class PersistentPythonEnvironment:
    def __init__(self):
        self.globals = {}
        self.locals = {}

    def execute(self, code):
        try:
            exec(code, self.globals, self.locals)
            return "Code executed successfully"
        except Exception as e:
            return f"Error executing code: {str(e)}"

    def get_state(self):
        return {**self.globals, **self.locals}

class Agent:
    def __init__(self, goal, backend_name):
        self.main_llm = get_llm_backend(backend_name)
        self.single_llm = get_llm_backend(backend_name)
        self.goal = goal
        self.profile = self.create_profile()
        self.memory = []
        self.plan = self.create_plan()
        self.current_step = 0
        self.python_env = PersistentPythonEnvironment()

    def create_profile(self):
        prompt = f"""Create a profile for an AI agent with the goal: {self.goal}. Include name, expertise, and key traits.
        Return the profile as a JSON object with the following structure:
        {{
            "name": "Agent name",
            "expertise": "Agent's area of expertise",
            "traits": ["trait1", "trait2", "trait3"]
        }}
        Provide only the JSON object in your response, with no additional text."""
        
        response = self.single_llm.communicate(prompt, reset=True)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "name": "Default Agent",
                "expertise": "General problem-solving",
                "traits": ["adaptive", "analytical", "persistent"]
            }

    def create_plan(self):
        prompt = f"""Create a high-level plan to achieve the following goal: {self.goal}.
        Provide a list of steps, each with a brief description of what needs to be done.
        At each step, you will be allowed to choose between python, search, or ask_llm to analyze the obtained information from the previous steps.
        Do not specify the exact type of action (python, search, or ask_llm) at this stage.
        Return the plan as a JSON array of strings. For example:
        [
            "Research current market trends",
            "Analyze competitor strategies",
            "Identify potential target audience",
            "Draft initial marketing plan"
        ]
        Provide only the JSON array in your response, with no additional text."""
        
        response = self.main_llm.communicate(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return ["Research the problem"]

    def next_action(self):
        if self.current_step < len(self.plan):
            step_description = self.plan[self.current_step]
            prompt = f"""Based on the following step in our plan, determine the most appropriate action to take:

            Step: {step_description}
            Current Goal: {self.goal}

            Specify the action as a JSON object with the following structure:
            {{
                "type": "python" or "search" or "ask_llm",
                "description": "Detailed description of the action",
                "code": "Python code to execute" (only if type is "python"),
                "query": "Search query to use" (only if type is "search"),
                "question": "Question to ask the LLM" (only if type is "ask_llm")
            }}
            Provide only the JSON object in your response, with no additional text."""

            response = self.main_llm.communicate(prompt)
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return None
        return None

    def execute_action(self, action):
        print(f"Executing action: {action['type']} - {action['description']}", file=sys.stderr)
        if action['type'] == 'python':
            result = self.python_env.execute(action['code'])
            print(f"Python environment state: {self.python_env.get_state()}", file=sys.stderr)
        elif action['type'] == 'search':
            result = search_duckduckgo(action['query'])
        elif action['type'] == 'ask_llm':
            result = self.single_llm.communicate(action['question'], reset=True)
        else:
            result = f"Unknown action type: {action['type']}"
        
        print(f"Action result: {result}", file=sys.stderr)
        return result

    def adjust_current_action(self, user_input):
        current_step = self.plan[self.current_step]
        python_state = self.python_env.get_state()
        prompt = f"""Based on the following information, adjust the current step:

        Current Goal: {self.goal}
        Current Step: {current_step}
        User Input: {user_input}
        Current Python Environment State: {json.dumps(python_state)}

        Please provide an updated step description that incorporates the user's input and considers the current Python environment state if applicable.
        Return the result as a simple string describing the adjusted step."""

        response = self.main_llm.communicate(prompt)
        self.plan[self.current_step] = response.strip()
        return self.next_action()

    def process_feedback(self, feedback):
        prompt = f"""Based on the following goal, current plan, and user feedback, determine if we should:
        1. Continue with the current plan
        2. Update the next steps of the current plan
        3. Create an entirely new plan

        Goal: {self.goal}

        Current Plan:
        {json.dumps(self.plan, indent=2)}

        Current Step: {self.current_step}

        User Feedback: {feedback}

        Memory:
        {json.dumps(self.memory, indent=2)}

        Provide your decision as a JSON object with the following structure:
        {{
            "decision": "continue" or "update_next_steps" or "new_plan",
            "reasoning": "Explanation for the decision",
            "updated_plan": [] (include only if decision is "update_next_steps" or "new_plan")
        }}
        """

        response = self.main_llm.communicate(prompt)
        try:
            decision = json.loads(response)
            if decision['decision'] == 'update_next_steps':
                self.plan = self.plan[:self.current_step] + decision['updated_plan']
            elif decision['decision'] == 'new_plan':
                self.plan = decision['updated_plan']
                self.current_step = 0
            return decision
        except json.JSONDecodeError:
            return {"decision": "continue", "reasoning": "Error processing feedback, continuing with current plan."}

    def update_memory(self, action, result):
        self.memory.append({"action": action, "result": result})

    def generate_conclusion(self):
        prompt = f"""Based on the following goal and actions taken, generate a comprehensive conclusion or final result.
        If the goal was a programming task, describe the project structure and key components created.
        If it was a research task, summarize the main findings and insights.

        Goal: {self.goal}

        Actions and Results:
        {json.dumps(self.memory, indent=2)}

        Please provide a detailed conclusion that addresses the original goal and synthesizes the information gathered or work completed.
        """

        conclusion = self.main_llm.communicate(prompt)
        return conclusion

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
    print(f"DuckDuckGo search query: {query}", file=sys.stderr)
    results = []
    try:
        with DDGS() as search_engine:
            for result in search_engine.text(query, safesearch="Off", max_results=3):
                title = result["title"]
                url = result["href"]
                result_text = f'*Title*: {title}\n*Body*: {result["body"]}\n*URL*: {url}'
                results.append(result_text)
        
        final_result = '\n\n'.join(results)
        print(f"DuckDuckGo search result: {final_result}", file=sys.stderr)
        return final_result if results else "No results found"
    except Exception as e:
        error_message = f"Error during DuckDuckGo search: {str(e)}"
        print(error_message, file=sys.stderr)
        return error_message
