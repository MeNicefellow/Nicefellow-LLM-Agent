from flask import Flask, render_template, request, jsonify
from agent import Agent

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
    if agent:
        action = agent.next_action()
        return jsonify(action)
    return jsonify(None)

@app.route('/execute_action', methods=['POST'])
def execute_action():
    if not agent:
        return jsonify({"error": "No agent created"}), 400
    
    action = request.json['action']
    allowed = request.json['allowed']
    
    if allowed:
        result = agent.execute_action(action)
        agent.update_memory(action, result)
        agent.current_step += 1
        return jsonify({"result": result, "agent": agent.to_dict()})
    else:
        return jsonify({"result": "Action not allowed", "agent": agent.to_dict()})

if __name__ == '__main__':
    app.run(debug=True)