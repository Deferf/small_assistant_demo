# app.py
from flask import Flask, request, jsonify, render_template
import openai
import requests
import json
import time
import config
 
app = Flask(__name__)
 
# Set your OpenAI API key here
openai.api_key = api_key = config.API_KEY
 
# Define a function to get the weather for a specific location
def get_weather(location):
    base_url = f"http://wttr.in/{location}"
    response = requests.get(base_url, params={'format': 'j1'})
    return response.json()
 
# Initialize the OpenAI client with the API key
client = openai.OpenAI(api_key=openai.api_key)
 
assistant_instructions = "The user is Andres. Help him out."
functions = [
    {
        "type": "function",
        "function": {
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Location name in English"
                    }
                },
                "required": ["location"]
            },
            "description": "Gets the weather",
            "name": "get_weather"
        }
    },
    {
        "type": "code_interpreter"
    }
]
 
# Create an assistant using the OpenAI client with the defined instructions and functions
assistant = client.beta.assistants.create(
    name="Weather getter",
    instructions=assistant_instructions,
    tools=functions,
    model="gpt-4-turbo-2024-04-09",
)
 
# Route for the main page
@app.route('/')
def index():
    return render_template('index.html')
 
# Route to handle chat messages
@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
 
    try:
        thread = client.beta.threads.create()
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )
 
        if run.status == 'completed':
            messages = list(client.beta.threads.messages.list(thread_id=thread.id))
            response_message = messages[0].content[0].text.value if messages else 'No response'
            return jsonify({'message': response_message})
        else:
            calls = run.required_action.submit_tool_outputs.tool_calls
            results = []
            for call in calls:
                name, arguments = call.function.name, call.function.arguments
                func_name = globals().get(name)
                result = func_name(json.loads(arguments)['location'])
                output = json.dumps(result)
                results.append({"tool_call_id": call.id, "output": output})
 
            run = client.beta.threads.runs.submit_tool_outputs_and_poll(
                thread_id=thread.id,
                run_id=run.id,
                tool_outputs=results
            )
 
            if run.status == 'completed':
                messages = list(client.beta.threads.messages.list(thread_id=thread.id))
                response_message = messages[0].content[0].text.value
                return jsonify({'message': f"called: {name} with arguments {arguments} <br>" + response_message})
            else:
                return jsonify({'error': 'Failed to get a valid response'}), 500
 
    except Exception as e:
        return jsonify({'error': str(e)}), 500
 
if __name__ == '__main__':
    app.run(debug=True)