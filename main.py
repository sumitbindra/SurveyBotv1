from flask import Flask, request, jsonify, render_template
import os
import openai
import psycopg2
import json

app = Flask(__name__, template_folder='templates')

#DATABASE = "survey.db"
DATABASE_URL = os.getenv('db_url')  # Replace this with your ElephantSQL URL

openai.api_key = os.getenv('llm_key')  # Replace with your key
conversation_history = []
DATA_FILE = "temp_data.json"

# ------- Include the state information here -------

# Global state and context variables
states = {
    "greeting": "Hello! I'm here to collect some demographic information. Type 'ready' to begin.",
    "name": "Please provide your name.",
    "age": "Thank you! Next, please tell me your age.",
    "income": "Thanks. Now, could you let me know your annual income?",
    "household_count": "Understood. How many people are there in your household?",
    "vehicle_count": "Got it. How many vehicles do you have?",
    "children_count": "Thanks. Finally, how many children are there in your household?"
}

current_state = "greeting"

chat_context = [
    {"role": "system", "content": "You are a survey assistant collecting demographic information."},
    {"role": "assistant", "content": states[current_state]}
]

row_id = None

# --------------------------------------------------

def init_db():
    with psycopg2.connect(DATABASE_URL, sslmode='require') as conn:
        cursor = conn.cursor()
        
        # Create table - adjust the fields as per your requirement
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            income REAL,
            household_count INTEGER,
            vehicle_count INTEGER,
            children_count INTEGER
        )
        """)
        
        conn.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/init', methods=['GET'])
def init():
    return jsonify({"message": states["greeting"]})
  
@app.route('/chat', methods=['POST'])
def chat():
    global current_state
    global chat_context
    global row_id

    user_message = request.json.get('message')
    chat_context.append({"role": "user", "content": user_message})

    response_message = ""

    # Always initialize an empty dictionary at the start
    data = {}

    # Load existing data if the file exists
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as file:
            data = json.load(file)

    # State handlers
    if current_state == "greeting":
        if user_message.lower() == 'ready':
            response_message = states["name"]
            current_state = "name"
        else:
            response_message = "Type 'ready' to begin."
    
    elif current_state == "name":
        data["name"] = user_message
        response_message = states["age"]
        current_state = "age"

    elif current_state == "age":
        try:
            age = int(user_message)
            if 0 < age <= 120:
                data["age"] = age  # Store the age.
                response_message = states["income"]  # Ask for income next.
                current_state = "income"
            else:
                response_message = "Please provide a reasonable age."
        except ValueError:
            response_message = "Please provide a valid age."
    
    elif current_state == "income":
        try:
            income = float(user_message)
            data["income"] = income
            response_message = states["household_count"]
            current_state = "household_count"
        except ValueError:
            response_message = "Please provide a valid income amount."
    
    elif current_state == "household_count":
        try:
            household_count = int(user_message)
            data["household_count"] = household_count
            response_message = states["vehicle_count"]
            current_state = "vehicle_count"
        except ValueError:
            response_message = "Please provide a valid number for household count."

    elif current_state == "vehicle_count":
        try:
            vehicle_count = int(user_message)
            data["vehicle_count"] = vehicle_count
            response_message = states["children_count"]
            current_state = "children_count"
        except ValueError:
            response_message = "Please provide a valid number for vehicle count."

    elif current_state == "children_count":
        try:
            children_count = int(user_message)
            data["children_count"] = children_count
            #response_message = "Thanks for providing your information!"
            current_state = "completed"
        except ValueError:
            response_message = "Please provide a valid number for children count."

        # Validate all data
        required_fields = ["name", "age", "income", "household_count", "vehicle_count", "children_count"]
        if all(field in data for field in required_fields):
            with psycopg2.connect(DATABASE_URL, sslmode='require') as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO responses (name, age, income, household_count, vehicle_count, children_count) VALUES (%s, %s, %s, %s, %s, %s)", 
                                (data["name"], data["age"], data["income"], data["household_count"], data["vehicle_count"], data["children_count"]))
                conn.commit()
    
            os.remove(DATA_FILE)  # Clear the temporary data
            response_message = "Thank you for providing all the information!"
        else:
            response_message = "Some information seems missing. Please continue."

    # Save data
    with open(DATA_FILE, 'w') as file:
        json.dump(data, file)

    return jsonify({"message": response_message})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=81)
