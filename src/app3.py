from flask import Flask, request, jsonify, render_template
import openai
import requests
import config

app = Flask(__name__)

# Set your OpenAI API key here
openai.api_key = config.API_KEY


# Define a function to get the weather for a specific location
def get_weather(location):
    base_url = f"http://wttr.in/{location}"
    response = requests.get(base_url, params={'format': 'j1'})
    return response.json()

# Initialize the OpenAI client
client = openai.OpenAI(api_key=openai.api_key)

# Instructions for the assistant
assistant_instructions = "The user is Andres. Help him out."

# Define the tools that the assistant can call
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
                "required": [
                    "location"
                ]
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

# Create a new thread for the assistant to interact within
thread = client.beta.threads.create()




@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']

    message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content=user_message
)

    # Here we run inference on the information above
    # We poll the model until it is completed processing
    run = client.beta.threads.runs.create_and_poll(
      thread_id=thread.id,
      assistant_id=assistant.id,
    )

    # Print messages if response is textual, otherwise print the status
    if run.status == 'completed':
      messages = client.beta.threads.messages.list(thread_id=thread.id)
      return jsonify({'message': messages})
    else:
      return jsonify({'message': run.status})
    
    return jsonify({'message': "default reponse: test message!"})

if __name__ == '__main__':
    app.run(debug=True)
