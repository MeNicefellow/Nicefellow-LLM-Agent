import os
from openai import OpenAI
from utils import llm_chatter

class OpenAIBackend:
    def __init__(self, model="gpt-4o-mini"):
        self.model = model
        self.load_api_key()
        self.client = OpenAI(
            # This is the default and can be omitted
            api_key=self.api_key,
            )
        self.conversation_history = []
    def load_api_key(self):
        api_key_path = os.path.join(os.path.expanduser("~"), ".openai_api_key")
        try:
            with open(api_key_path, 'r') as file:
                self.api_key = file.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"OpenAI API key file not found. Please create a file named .openai_api_key in your home directory ({os.path.expanduser('~')}) containing your OpenAI API key.")

    def communicate(self, prompt, reset=False):
        if reset:
            self.conversation_history = []

        self.conversation_history.append({"role": "user", "content": prompt})
        print("="*10)
        #print("conversation_history:")
        #for item in self.conversation_history:
        #    print('---\n',item['role'],item['content'])
        print('---\n',self.conversation_history[-1]['role'],self.conversation_history[-1]['content'])
        #print("="*10)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history
            )
            assistant_message = response.choices[0].message.content.strip()
            print("*"*10)
            print("assistant_message:\n",assistant_message)
            print("*"*10)
            if assistant_message.startswith("```json\n") and assistant_message.endswith("```"):
                assistant_message = assistant_message[len("```json\n"):-len("```")]
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            return assistant_message
        except Exception as e:
            print(f"Error communicating with OpenAI API: {str(e)}")
            return "Error: Unable to get response from OpenAI API"

class DefaultBackend(llm_chatter):
    pass


def get_llm_backend(backend_name):
    if backend_name.lower() == "openai":
        return OpenAIBackend()
    elif backend_name.lower() == "llm_chatter":
        return DefaultBackend()
    else:
        raise ValueError(f"Unknown backend: {backend_name}. Please choose 'openai' or 'llm_chatter'.")