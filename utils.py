import requests



class ollama_chatter:
    def __init__(self, host='http://localhost:11434'):
        self.host = host
        self.msg_history = []
        self.headers = {
            "Content-Type": "application/json"
        }

    def communicate(self, prompt, greedy=True, reset=True, max_tokens=4096):
        f = codecs.open("conversation_history.txt", "a", "utf-8")
        if reset:
            self.msg_history = []
        self.msg_history.append({"role": "user", "content": prompt})

        f.write("=" * 10 + "\n")
        for item in self.msg_history:
            f.write(item['role'] + ":\n" + str(item['content']) + "\n")

        # Configure the request data
        data = {
            "model": "qwen2.5-7b",  # This can be made configurable
            "messages": self.msg_history,
            "stream": False,
            "options": {
                "num_predict": max_tokens,  # This corresponds to max_tokens
                "temperature": 0.001 if not greedy else 0,
            }
        }

        # Make the API call
        response = requests.post(f"{self.host}/api/chat", headers=self.headers, json=data)
        
        # Extract the response content
        # Note: Ollama's response format might need adjustment depending on the actual response structure
        answer = json.loads(response.content.decode())['message']['content']
        
        f.write("-" * 10 + "\n" + "response:\n")
        f.write(answer + "\n")
        f.close()
        
        self.msg_history.append({"role": "assistant", "content": answer})

        # Process special formats (JSON/YAML)
        assistant_message = answer
        
        # Extract JSON if present
        if "```json" in assistant_message:
            json_start = assistant_message.index("```json") + 7
            json_end = assistant_message.rindex("```", json_start)
            json_str = assistant_message[json_start:json_end].strip()
            try:
                assistant_message = json.loads(json_str)
            except json.JSONDecodeError:
                print("Warning: Failed to parse JSON. Returning original message.")
                print("-=-=-=-=\nJsonstring:\n")
                print(json_str)
                print("-=-=-=-=")
        # Extract YAML if present
        elif "```yaml" in assistant_message or "```yml" in assistant_message:
            yaml_start = assistant_message.index("```yaml") + 7 if "```yaml" in assistant_message else assistant_message.index("```yml") + 6
            yaml_end = assistant_message.rindex("```", yaml_start)
            yaml_str = assistant_message[yaml_start:yaml_end].strip()
            try:
                assistant_message = yaml.safe_load(yaml_str)
            except yaml.YAMLError:
                print("Warning: Failed to parse YAML. Returning original message.")
                print("-=-=-=-=\nYamlstring:\n")
                print(yaml_str)
                print("-=-=-=-=")

        return assistant_message

class llm_chatter:
    def __init__(self,host='http://127.0.0.1:1234/v1/chat/completions'):
        self.host = host
        self.msg_history = []
        self.headers = {
            "Content-Type": "application/json"
        }
    def communicate(self,prompt,greedy=True,reset=False,max_tokens=2048,template="Llama-v3"):
        if reset:
            self.msg_history = []
        self.msg_history.append({"role": "user", "content": prompt})
        data = {
            "mode": "instruct",
            "max_tokens": max_tokens,
            "instruction_template":template,
                "messages": self.msg_history
        }
        if greedy:
            data['temperature'] = 0
        response = requests.post(self.host, headers=self.headers, json=data, verify=False)
        answer = response.json()['choices'][0]['message']['content']
        self.msg_history.append({"role": "assistant", "content": answer})
        return answer

class llm_completion:
    def __init__(self,host='http://127.0.0.1:5000/v1/completions'):
        self.host = host
        self.headers = {
            "Content-Type": "application/json"
        }
    def complete(self,prompt,greedy=False,max_tokens=2048):
        data = {
            "max_tokens": max_tokens,
            "prompt": prompt,
            "temperature": 1,
            "top_p": 0.9,
        }
        if greedy:
            data['temperature'] = 0
        response = requests.post(self.host, headers=self.headers, json=data, verify=False)
        answer = response.json()['choices'][0]['text']
        return answer
