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

@app.route('/')
def index():
    return render_template('index2.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']

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
                    "required": [
                        "location"
                    ]
                },
                "description": "Gets the weather",
                "name": "get_weather"
            }
        }
    ]

    # Create an assistant using the OpenAI client
    assistant = client.assistants.create(
        name="Weather getter",
        instructions=assistant_instructions,
        tools=functions,
        model="gpt-4-turbo-2024-04-09",
    )

    # Create a new thread for the assistant to interact within
    thread = client.threads.create()

    # The conversation starts with a User message
    message = client.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_message
    )

    # Run inference on the information above
    run = client.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )

    if run.status == 'requires_action':
        calls = run.required_action.submit_tool_outputs.tool_calls
        results = []
        for call in calls:
            id = call.id
            name, arguments = call.function.name, call.function.arguments
            output = get_weather(arguments['location'])
            results.append({"tool_call_id": id, "output": output})

        # Submit results to model
        run = client.threads.runs.submit_tool_outputs_and_poll(
            thread_id=thread.id,
            run_id=run.id,
            tool_outputs=results
        )

    # Show the whole conversation
    messages = client.threads.messages.list(thread_id=thread.id, order="asc")

    conversation = "\n".join(
        [f"USER: {m.content[0].text.value}" if m.assistant_id is None else f"ASSISTANT: {m.content[0].text.value}" for m in messages]
    )

    return jsonify({"conversation": conversation})

if __name__ == '__main__':
    app.run(debug=True)
