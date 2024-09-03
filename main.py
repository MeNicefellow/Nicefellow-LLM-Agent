from flask import Flask, render_template, request, jsonify
from agent import Agent
import subprocess
import requests

app = Flask(__name__)

agent = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_agent', methods=['POST'])
def create_agent():
    global agent
    goal = request.json['goal']
    agent = Agent(goal)
    return jsonify(agent.to_dict())

@app.route('/next_action', methods=['GET'])
def next_action():
    action = agent.next_action()
    return jsonify({"action": action})

@app.route('/execute_action', methods=['POST'])
def execute_action():
    action = request.json['action']
    allowed = request.json['allowed']
    
    if allowed:
        result = agent.execute_action(action)
        agent.update_memory(action, result)
        agent.current_step += 1
        return jsonify({"result": result, "agent": agent.to_dict()})
    else:
        return jsonify({"result": "Action not allowed", "agent": agent.to_dict()})

def execute_python_code(code):
    try:
        result = subprocess.run(['python', '-c', code], capture_output=True, text=True, timeout=10)
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Execution timed out"
    except Exception as e:
        return str(e)

def search_duckduckgo(query):
    url = f"https://api.duckduckgo.com/?q={query}&format=json"
    response = requests.get(url)
    return response.json()

if __name__ == '__main__':
    app.run(debug=True)