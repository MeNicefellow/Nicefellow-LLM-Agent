from utils import llm_chatter
from llm_backends import get_llm_backend
import json
import sys
from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup
import io
import types
import os
from datetime import datetime
import subprocess
import shlex

class PersistentPythonEnvironment:
    def __init__(self):
        self.globals = {}
        self.locals = {}

    def execute(self, code):
        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output

        try:
            exec(code, self.globals, self.locals)
            output = redirected_output.getvalue()
            result = {
                "status": "success",
                "output": output,
                "state": self.get_state()
            }
        except Exception as e:
            result = {
                "status": "error",
                "error_message": str(e),
                "state": self.get_state()
            }
        finally:
            sys.stdout = old_stdout

        return result

    def get_state(self):
        def is_simple_variable(obj):
            return not isinstance(obj, (types.FunctionType, types.ModuleType, type))

        local_vars = {k: str(v) for k, v in self.locals.items() if is_simple_variable(v)}
        #print("local_vars:",local_vars)
        return local_vars#{k: str(v) for k, v in {**self.globals, **self.locals}.items()}

class Agent:
    def __init__(self, goal, backend_name='openai'):
        self.main_llm = get_llm_backend(backend_name)
        self.single_llm = get_llm_backend(backend_name)
        self.goal = goal
        self.profile = self.create_profile()
        self.memory = []
        self.project_folder = self.create_project_folder()
        self.plan = self.create_plan()
        self.current_step = 0
        self.python_env = PersistentPythonEnvironment()
        self.next_action = self.generate_next_action()  # Generate the first action

    def create_project_folder(self):
        base_folder = "./workspace"
        if not os.path.exists(base_folder):
            os.makedirs(base_folder)
        project_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_folder = os.path.join(base_folder, f"project_{project_datetime}")
        os.makedirs(project_folder)
        return project_folder

    def create_plan(self):
        prompt = f"""Create a high-level plan to achieve the following goal: {self.goal}.
        Provide a list of steps, each with a brief description of what needs to be done.
        You can include steps to adjust the plan or visit web pages if necessary.
        Return the plan as a JSON array of strings. For example:
        [
            "Research current market trends",
            "Analyze competitor strategies",
            "Adjust plan based on findings",
            "Visit product website for detailed information",
            "Draft initial marketing plan"
        ]
        Provide only the JSON array in your response, with no additional text."""
        
        response = self.main_llm.communicate(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return ["Research the problem"]

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

    def generate_next_action(self):
        print(f"-=-=-=-=-=-=-=-=-=-=Current step: {self.current_step}")
        if self.current_step < len(self.plan):
            step_description = self.plan[self.current_step]
            context = self.get_memory_context()
            prompt = f"""Context:
{context}

Current Goal: {self.goal}
Current Step: {step_description}

Based on the current step and context, determine the next action to take.
If you believe the current step has been accomplished, respond with: {{"type": "step_completed"}}

Otherwise, specify the action as a JSON object with the following structure:
{{
    "type": "python" or "search" or "ask_llm" or "adjust_plan" or "visit_page" or "writetofile" or "command",
    "description": "Detailed description of the action",
    "code": "Python code to execute" (only if type is "python"),
    "query": "Search query to use" (only if type is "search"),
    "question": "Question to ask the LLM" (only if type is "ask_llm"),
    "adjustment_prompt": "Prompt for plan adjustment" (only if type is "adjust_plan"),
    "url": "URL to visit" (only if type is "visit_page"),
    "file_path": "Relative path of the file to write" (only if type is "writetofile"),
    "file_content": "Content to write to the file" (only if type is "writetofile"),
    "command": "Shell command to execute" (only if type is "command")
}}

Note: 
- For the "writetofile" action, the file_path should be relative to the project folder. All files will be written within the folder: {self.project_folder}
- For the "command" action, the command will be executed in the project folder: {self.project_folder}. Be cautious with system commands and avoid destructive operations.

Provide only the JSON object in your response, with no additional text."""

            response = self.main_llm.communicate(prompt)
            try:
                action = json.loads(response)
                if action.get("type") == "step_completed":
                    self.current_step += 1
                    return self.generate_next_action()
                return action
            except json.JSONDecodeError:
                return None
        return {"type": "plan_completed", "description": "All steps in the plan have been completed."}

    def execute_action(self, action):
        print("action:",action)
        #print(f"Executing action: {action['type']} - {action['description']}", file=sys.stderr)
        if action['type'] == 'python':
            result = self.python_env.execute(action['code'])
            #print(f"Python environment state: {self.python_env.get_state()}", file=sys.stderr)
        elif action['type'] == 'search':
            result = search_duckduckgo(action['query'])
        elif action['type'] == 'ask_llm':
            context = self.get_memory_context()
            question = f"""Context:
{context}

Given the above context, please answer the following question:
{action['question']}"""
            result = self.single_llm.communicate(question, reset=True)
        elif action['type'] == 'adjust_plan':
            result = self.adjust_plan(action['adjustment_prompt'])
        elif action['type'] == 'visit_page':
            result = self.visit_page(action['url'])
        elif action['type'] == 'writetofile':
            result = self.write_to_file(action['file_path'], action['file_content'])
        elif action['type'] == 'command':
            result = self.execute_command(action['command'])
        else:
            result = f"Unknown action type: {action['type']}"
        
        #print(f"Action result: {result}", file=sys.stderr)
        self.update_memory(action, result)
        return result

    def check_step_completion(self, action_result):
        context = self.get_memory_context()
        current_step = self.plan[self.current_step]
        prompt = f"""Context:
{context}

Current Goal: {self.goal}
Current Step: {current_step}
Last Action Result: {action_result}

Based on the context, current step, and the result of the last action, determine if the current step has been accomplished. If it cannot be achieved for any reason including technical reasons, please still mark it as completed so as to go to next step.
Respond with a JSON object in the following format:
{{
    "completed": true or false,
    "reasoning": "Explanation for why the step is completed or not"
}}
Provide only the JSON object in your response, with no additional text."""

        response = self.main_llm.communicate(prompt)
        try:
            completion_status = json.loads(response)
            return completion_status
        except json.JSONDecodeError:
            return {"completed": False, "reasoning": "Error parsing LLM response"}

    def adjust_plan(self, adjustment_prompt):
        context = self.get_memory_context()
        prompt = f"""Context:
{context}

Current plan:
{json.dumps(self.plan, indent=2)}

Current step: {self.current_step}

Based on the above context and the following prompt, adjust the remaining steps of the plan:
{adjustment_prompt}

Return the adjusted plan as a JSON array of strings, starting from the current step."""

        response = self.main_llm.communicate(prompt)
        try:
            adjusted_plan = json.loads(response)
            self.plan = self.plan[:self.current_step] + adjusted_plan
            return f"Plan adjusted. New plan: {json.dumps(self.plan, indent=2)}"
        except json.JSONDecodeError:
            return "Failed to adjust the plan due to invalid JSON response."

    def get_memory_context(self):
        context = "Previous actions and results:\n\n"
        for item in self.memory:
            context += f"Action: {json.dumps(item['action'])}\n"
            context += f"Result: {item['result']}\n\n"
        return context

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
        return self.generate_next_action()
    def visit_page(self, url):
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract text content
            text_content = soup.get_text(separator='\n', strip=True)
            
            # Truncate if too long
            max_length = 5000  # Adjust as needed
            if len(text_content) > max_length:
                text_content = text_content[:max_length] + "...(truncated)"
            
            return f"Content from {url}:\n\n{text_content}"
        except Exception as e:
            return f"Error visiting page {url}: {str(e)}"
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
        prompt = f"""Based on the following goal and actions taken, generate a brief and concise conclusion.
        If the goal was to find or calculate something, just provide the result.
        If it was a research task, summarize the main finding in one sentence.

        Goal: {self.goal}

        Actions and Results:
        {json.dumps(self.memory, indent=2)}

        Please provide a single sentence or a simple list that directly addresses the original goal.
        """

        conclusion = self.main_llm.communicate(prompt)
        return conclusion

    def to_dict(self):
        return {
            "goal": self.goal,
            "profile": self.profile,
            "memory": self.memory,
            "plan": self.plan,
            "current_step": self.current_step,
            "project_folder": self.project_folder,
            "next_action": self.next_action  # Include the next_action in the dictionary
        }

    def is_plan_completed(self):
        return self.current_step >= len(self.plan)

    def write_to_file(self, relative_path, content):
        full_path = os.path.join(self.project_folder, relative_path)
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)
            return f"File successfully written to {relative_path}"
        except Exception as e:
            return f"Error writing to file {relative_path}: {str(e)}"

    def execute_command(self, command):
        try:
            # Use shlex.split to properly handle command arguments
            args = shlex.split(command)
            # Execute the command in the project folder
            process = subprocess.Popen(args, cwd=self.project_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                return f"Command executed successfully. Output:\n{stdout}"
            else:
                return f"Command failed with return code {process.returncode}. Error:\n{stderr}"
        except Exception as e:
            return f"Error executing command: {str(e)}"

def exec_python_code(code):
    # This is a simplified version. In a real-world scenario, you'd want to add more security measures
    try:
        exec_globals = {}
        exec(code, exec_globals)
        return str(exec_globals.get('result', 'Code executed successfully'))
    except Exception as e:
        return f"Error executing code: {str(e)}"

def search_duckduckgo(query):
    #print(f"DuckDuckGo search query: {query}", file=sys.stderr)
    results = []
    try:
        with DDGS() as search_engine:
            for result in search_engine.text(query, safesearch="Off", max_results=5):
                title = result["title"]
                url = result["href"]
                result_text = f'*Title*: {title}\n*Body*: {result["body"]}\n*URL*: {url}'
                results.append(result_text)
        
        final_result = '\n\n'.join(results)
        #print(f"DuckDuckGo search result: {final_result}", file=sys.stderr)
        return final_result if results else "No results found"
    except Exception as e:
        error_message = f"Error during DuckDuckGo search: {str(e)}"
        print(error_message, file=sys.stderr)
        return error_message
