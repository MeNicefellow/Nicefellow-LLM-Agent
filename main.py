from flask import Flask, render_template, request, jsonify
from agent import Agent
import traceback
import os

app = Flask(__name__)

agent = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_agent', methods=['POST'])
def create_agent():
    global agent
    goal = request.json['goal']
    backend = request.json.get('backend', 'openai')  # Default to 'openai' if not specified
    agent = Agent(goal, backend)
    return jsonify(agent.to_dict())

@app.route('/next_action', methods=['GET'])
def next_action():
    if agent:
        action = agent.generate_next_action()
        return jsonify(action)
    return jsonify(None)

@app.route('/execute_action', methods=['POST'])
def execute_action():
    global agent
    if not agent:
        return jsonify({"error": "No agent created"}), 400
    
    try:
        data = request.json
        action = data.get('action')
        allowed = data.get('allowed')
        
        if action is None or allowed is None:
            return jsonify({"error": "Missing action or allowed parameter"}), 400

        print(f"Executing action: {action}, Allowed: {allowed}")  # Debug print
        
        if allowed:
            result = agent.execute_action(action)
            completion_status = agent.check_step_completion(result)
            
            if completion_status['completed']:
                agent.current_step += 1
            
            next_action = agent.generate_next_action()
            
            return jsonify({
                "result": result,
                "completion_status": completion_status,
                "agent": agent.to_dict(),
                "next_action": next_action,
                "plan_completed": agent.is_plan_completed()
            })
        else:
            next_action = agent.generate_next_action()
            return jsonify({
                "result": "Action not allowed",
                "agent": agent.to_dict(),
                "next_action": next_action,
                "plan_completed": agent.is_plan_completed()
            })
    except Exception as e:
        print(f"Error in execute_action: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/generate_conclusion', methods=['GET'])
def generate_conclusion():
    if not agent:
        return jsonify({"error": "No agent created"}), 400
    
    conclusion = agent.generate_conclusion()
    return jsonify({"conclusion": conclusion})

@app.route('/process_feedback', methods=['POST'])
def process_feedback():
    if not agent:
        return jsonify({"error": "No agent created"}), 400
    
    feedback = request.json['feedback']
    decision = agent.process_feedback(feedback)
    return jsonify({"decision": decision, "agent": agent.to_dict()})

@app.route('/adjust_action', methods=['POST'])
def adjust_action():
    if not agent:
        return jsonify({"error": "No agent created"}), 400
    
    user_input = request.json['user_input']
    updated_action = agent.adjust_current_action(user_input)
    return jsonify({"updated_action": updated_action, "agent": agent.to_dict()})

@app.route('/get_project_files', methods=['GET'])
def get_project_files():
    if not agent:
        return jsonify({"error": "No agent created"}), 400
    
    project_files = []
    for root, dirs, files in os.walk(agent.project_folder):
        for file in files:
            full_path = os.path.join(root, file)
            relative_path = os.path.relpath(full_path, agent.project_folder)
            project_files.append(relative_path)
    
    return jsonify({"project_files": project_files})

if __name__ == '__main__':
    app.run(debug=True)