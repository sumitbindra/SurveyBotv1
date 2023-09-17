from flask import Flask, request, jsonify, render_template
import os
import openai
import sqlite3

app = Flask(__name__, template_folder='templates')

DATABASE = "survey.db"
openai.api_key = os.getenv('llm_key')  # Replace with your key
conversation_history = []

# ------- Include the state information here -------

# Global state and context variables
states = {
    "name": "What is your name?",
    "age": "How old are you?",
    "income": "What is your annual income?",
    "household": "How many people are in your household?",
    "vehicles": "How many vehicles do you have?",
    "children": "How many children do you have?",
    "completed": "Thank you for providing your information!"
}
current_state = "name"

chat_context = [
    {"role": "system", "content": "You are a survey assistant collecting demographic information."},
    {"role": "assistant", "content": states[current_state]}
]

# --------------------------------------------------

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY,
                name TEXT,
                age INTEGER,
                income REAL,
                household_count INTEGER,
                vehicle_count INTEGER,
                children_count INTEGER
            )
        """)

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    global current_state
    global chat_context

    user_message = request.json.get('message')
    chat_context.append({"role": "user", "content": user_message})

    # Predefined logic-based checks
    # Logic checks for name state
    if current_state == "name":
        # Save name to the database
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO responses (name) VALUES (?)", (user_message,))
            conn.commit()

        response_message = states["age"]
        current_state = "age"
    # Other logic-based checks
    elif current_state == "age" and not user_message.isdigit():
        response_message = "Please provide a valid age."
    elif current_state == "income" and not user_message.replace('.', '', 1).isdigit():
        response_message = "Please provide a valid income number."
    elif current_state == "household" and not user_message.isdigit():
        response_message = "Please provide a valid number of people in your household."
    elif current_state == "vehicles" and not user_message.isdigit():
        response_message = "Please provide a valid number of vehicles."
    elif current_state == "children" and not user_message.isdigit():
        response_message = "Please provide a valid number of children."
    elif current_state == "children" and int(user_message) > int(chat_context[-2]['content']):  # Checking if children > household
        response_message = "The number of children can't be greater than the number of people in the household. Please provide a valid number."
    else:
        # If no immediate logic-based response, get the model's response
        response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=chat_context)
        response_message = response.choices[0].message['content']
        chat_context.append({"role": "assistant", "content": response_message})

        # Save data to the database based on current state
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            if current_state == "name":
                cursor.execute("INSERT INTO responses (name) VALUES (?)", (user_message,))
                current_state = "age"
            elif current_state == "age":
                cursor.execute("UPDATE responses SET age = ? WHERE id = last_insert_rowid()", (user_message,))
                current_state = "income"
            elif current_state == "income":
                cursor.execute("UPDATE responses SET income = ? WHERE id = last_insert_rowid()", (float(user_message),))
                current_state = "household"
            elif current_state == "household":
                cursor.execute("UPDATE responses SET household_count = ? WHERE id = last_insert_rowid()", (user_message,))
                current_state = "vehicles"
            elif current_state == "vehicles":
                cursor.execute("UPDATE responses SET vehicle_count = ? WHERE id = last_insert_rowid()", (user_message,))
                current_state = "children"
            elif current_state == "children":
                cursor.execute("UPDATE responses SET children_count = ? WHERE id = last_insert_rowid()", (user_message,))
                current_state = "completed"
            conn.commit()

    return jsonify({"message": response_message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)
