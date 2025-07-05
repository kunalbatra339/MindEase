from flask import Flask, jsonify, request
from flask_cors import CORS # Keep CORS
from datetime import datetime
import os
import requests
import json
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from pymongo import MongoClient # Import MongoClient directly
# from flask_pymongo import PyMongo # REMOVED: No longer using Flask-PyMongo

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# --- MongoDB Configuration ---
# IMPORTANT FOR DEPLOYMENT:
# When deploying to Render (or any other hosting platform), you MUST set the
# MONGO_URI environment variable in Render's dashboard with your actual connection string.
# Example: MONGO_URI = "mongodb+srv://kbatra339:kunal8ballpool@cluster0.wgcc4j6.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
# For local development, you can set this in your local environment variables
# or use a local MongoDB URI as a fallback.
MONGO_URI = os.environ.get("MONGO_URI", "") # Fallback to a local URI

# Initialize MongoDB client and database directly
# This is the change from Flask-PyMongo to direct PyMongo
db = None # Initialize db as None
try:
    client = MongoClient(MONGO_URI)
    # The 'ping' command is on the client.admin object for connection check
    client.admin.command('ping') 
    db = client['mindease_db'] # Specify your database name here (e.g., 'mindease_db')
    print("MongoDB connected successfully!")
    db_status_message = "connected"
except Exception as e:
    print(f"MongoDB connection error: {e}")
    db_status_message = f"error: {e}"
    # db remains None if connection fails

# Gemini API Configuration
# IMPORTANT FOR DEPLOYMENT:
# When deploying to Render, you MUST set the GEMINI_API_KEY environment variable
# in Render's dashboard with your actual Gemini API key.
# The empty string "" as a fallback ensures that if the environment variable is
# not set (e.g., locally), the API key will be missing, prompting you to set it.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "") 
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Helper function to get sentiment from LLM
def get_sentiment_from_llm(text):
    """
    Calls the Gemini API to get a sentiment analysis for the given text.
    Returns a string like 'positive', 'neutral', 'negative', or 'mixed'.
    """
    prompt = f"""Analyze the sentiment of the following journal entry. Respond with a single word: positive, neutral, negative, or mixed.

    Journal Entry:
    "{text}"

    Sentiment:"""

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2, # Lower temperature for more deterministic sentiment
            "maxOutputTokens": 10
        }
    }

    headers = {
        'Content-Type': 'application/json'
    }
    
    # This line correctly uses the GEMINI_API_KEY from the environment variable
    GEMINI_API_URL_WITH_KEY = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"

    try:
        response = requests.post(GEMINI_API_URL_WITH_KEY, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        
        gemini_response = response.json()
        
        if gemini_response and gemini_response.get('candidates'):
            sentiment = gemini_response['candidates'][0]['content']['parts'][0]['text'].strip().lower()
            if sentiment in ['positive', 'neutral', 'negative', 'mixed']:
                return sentiment
            else:
                return "unknown"
        else:
            return "unknown"

    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API for sentiment: {e}")
        return "error"
    except Exception as e:
        print(f"Unexpected error processing LLM sentiment response: {e}")
        return "error"

@app.route('/')
def home():
    """
    Root endpoint to check backend status and database connection.
    """
    return jsonify({
        "status": "success",
        "message": "MindEase Backend API is running!",
        "database_status": db_status_message
    })

# --- Custom Authentication Endpoints ---

@app.route('/register', methods=['POST'])
def register_user():
    """
    Endpoint for user registration.
    Expects JSON: {"username": "user123", "password": "securepassword"}
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    
    if db is None: # Check if DB connection failed at startup
        return jsonify({"error": "Database connection not available"}), 500

    if db.users.find_one({"username": username}): # NOW uses db.users
        return jsonify({"error": "Username already exists"}), 409

    hashed_password = generate_password_hash(password)

    user_data = {
        "username": username,
        "password": hashed_password
    }

    try:
        db.users.insert_one(user_data) # NOW uses db.users
        return jsonify({"message": "User registered successfully!"}), 201
    except Exception as e:
        return jsonify({"error": f"Registration failed: {e}"}), 500

@app.route('/login', methods=['POST'])
def login_user():
    """
    Endpoint for user login.
    Expects JSON: {"username": "user123", "password": "securepassword"}
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    
    if db is None: # Check if DB connection failed at startup
        return jsonify({"error": "Database connection not available"}), 500

    user = db.users.find_one({"username": username}) # NOW uses db.users

    if user and check_password_hash(user['password'], password):
        return jsonify({"message": "Login successful!", "username": username}), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401

@app.route('/change_password/<username>', methods=['PUT'])
def change_password(username):
    """
    Endpoint for changing user password.
    Expects JSON: {"old_password": "oldpassword", "new_password": "newpassword"}
    """
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    if not old_password or not new_password:
        return jsonify({"error": "Old password and new password are required"}), 400
    
    if db is None: # Check if DB connection failed at startup
        return jsonify({"error": "Database connection not available"}), 500

    user = db.users.find_one({"username": username}) # NOW uses db.users

    if not user:
        return jsonify({"error": "User not found"}), 404

    if not check_password_hash(user['password'], old_password):
        return jsonify({"error": "Incorrect old password"}), 401

    hashed_new_password = generate_password_hash(new_password)

    try:
        db.users.update_one( # NOW uses db.users
            {"username": username},
            {"$set": {"password": hashed_new_password}}
        )
        return jsonify({"message": "Password updated successfully!"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update password: {e}"}), 500

# --- Journal Endpoints ---

@app.route('/journal/<username>', methods=['POST'])
def add_journal_entry(username):
    """
    Endpoint to add a new journal entry for a specific user,
    including LLM-generated sentiment.
    Expects JSON: {"text": "Your journal entry here"}
    """
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "Missing 'text' field in request"}), 400
    
    if db is None: # Check if DB connection failed at startup
        return jsonify({"error": "Database connection not available"}), 500

    entry_text = data['text']
    timestamp = datetime.now()

    sentiment = get_sentiment_from_llm(entry_text)
    print(f"Generated sentiment for entry: '{entry_text[:30]}...' is '{sentiment}'")

    journal_entry = {
        "text": entry_text,
        "timestamp": timestamp,
        "date_display": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "username": username,
        "sentiment": sentiment # Store the sentiment
    }

    try:
        result = db.journal_entries.insert_one(journal_entry) # NOW uses db.journal_entries
        
        return jsonify({
            "message": "Journal entry added successfully!",
            "id": str(result.inserted_id),
            "entry": {
                "id": str(result.inserted_id),
                "text": entry_text,
                "date": journal_entry["date_display"],
                "sentiment": sentiment # Include sentiment in the response
            }
        }), 201
    except Exception as e:
        return jsonify({"error": f"Failed to save journal entry: {e}"}), 500

@app.route('/journal/<username>', methods=['GET'])
def get_journal_entries(username):
    """
    Endpoint to retrieve all journal entries for a specific user.
    Returns a list of journal entries, sorted by timestamp descending.
    """
    if db is None: # Check if DB connection failed at startup
        return jsonify({"error": "Database connection not available"}), 500

    try:
        entries_cursor = db.journal_entries.find({"username": username}).sort("timestamp", -1) # NOW uses db.journal_entries
        
        entries = []
        for entry in entries_cursor:
            entries.append({
                "id": str(entry['_id']),
                "text": entry['text'],
                "date": entry['date_display'],
                "sentiment": entry.get('sentiment', 'unknown') # Include sentiment, default to 'unknown' if not present
            })
        
        return jsonify(entries), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve journal entries: {e}"}), 500

@app.route('/journal/insight', methods=['POST'])
def get_journal_insight():
    """
    Endpoint to get an LLM-generated insight for a journal entry.
    Expects JSON: {"text": "The journal entry text"}
    """
    print("\n--- Insight Request Received ---")
    data = request.get_json()
    
    if not data or 'text' not in data:
        print("Insight Error: Missing 'text' field in insight request.")
        return jsonify({"error": "Missing 'text' field in request"}), 400
    
    # No DB check needed here as it's purely an LLM call

    journal_text = data['text']
    print(f"Insight Request Text: '{journal_text[:50]}...'")
    
    prompt = f"""Analyze the following journal entry and provide a concise, supportive, and insightful summary or reflection. Focus on identifying key emotions, themes, or potential areas for growth. Keep it under 100 words.

    Journal Entry:
    "{journal_text}"

    Insight:"""

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 200
        }
    }

    headers = {
        'Content-Type': 'application/json'
    }
    
    # This line correctly uses the GEMINI_API_KEY from the environment variable
    GEMINI_API_URL_WITH_KEY = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"

    try:
        print(f"Attempting call to Gemini API: {GEMINI_API_URL_WITH_KEY}")
        response = requests.post(GEMINI_API_URL_WITH_KEY, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        
        gemini_response = response.json()
        
        if gemini_response and gemini_response.get('candidates'):
            insight_text = gemini_response['candidates'][0]['content']['parts'][0]['text']
            print(f"Insight Generated Successfully: {insight_text[:50]}...")
            return jsonify({"insight": insight_text}), 200
        else:
            print("Insight Error: LLM returned no candidates or content (500).")
            return jsonify({"error": "No insight generated by LLM (LLM response empty or malformed)."}), 500

    except requests.exceptions.HTTPError as e:
        print(f"Insight Error: HTTP Error calling Gemini API: {e.response.status_code} - {e.response.text}")
        return jsonify({"error": f"Failed to get insight from LLM (HTTP Error): {e.response.status_code}"}), 500
    except requests.exceptions.RequestException as e:
        print(f"Insight Error: Network/Connection Error calling Gemini API: {e}")
        return jsonify({"error": f"Failed to get insight from LLM (Network Error): {e}"}), 500
    except Exception as e:
        print(f"Insight Error: An unexpected error occurred during insight generation: {e}")
        return jsonify({"error": f"An unexpected error occurred during insight generation: {e}"}), 500

# --- Endpoint for Sentiment Summary ---
@app.route('/journal/sentiment_summary/<username>', methods=['GET'])
def get_sentiment_summary(username):
    """
    Endpoint to retrieve a summary of sentiment counts for a specific user.
    Returns counts of 'positive', 'negative', 'neutral', 'mixed', and 'unknown' entries.
    """
    if db is None: # Check if DB connection failed at startup
        return jsonify({"error": "Database connection not available"}), 500

    try:
        pipeline = [
            {"$match": {"username": username}},
            {"$group": {"_id": "$sentiment", "count": {"$sum": 1}}}
        ]
        
        trends_cursor = db.journal_entries.aggregate(pipeline) # NOW uses db.journal_entries
        
        summary = {
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "mixed": 0,
            "unknown": 0,
            "total": 0
        }

        for item in trends_cursor: 
            sentiment_type = item['_id'] if item['_id'] else 'unknown'
            count = item['count']
            if sentiment_type in summary:
                summary[sentiment_type] = count
            else:
                summary['unknown'] += count
            summary['total'] += count
        
        return jsonify(summary), 200
    except Exception as e:
        print(f"Error getting sentiment summary: {e}")
        return jsonify({"error": f"Failed to retrieve sentiment summary: {e}"}), 500

# --- Endpoint for Updating Sentiment of a Specific Entry ---
@app.route('/journal/update_sentiment/<username>/<entry_id>', methods=['PUT'])
def update_journal_sentiment(username, entry_id):
    """
    Endpoint to update the sentiment of a specific journal entry.
    """
    if db is None: # Check if DB connection failed at startup
        return jsonify({"error": "Database connection not available"}), 500

    try:
        entry = db.journal_entries.find_one({"_id": ObjectId(entry_id), "username": username}) # NOW uses db.journal_entries
        
        if not entry:
            return jsonify({"error": "Journal entry not found or unauthorized"}), 404

        entry_text = entry['text']
        
        new_sentiment = get_sentiment_from_llm(entry_text)
        print(f"Updating sentiment for entry {entry_id} to: {new_sentiment}")

        db.journal_entries.update_one( # NOW uses db.journal_entries
            {"_id": ObjectId(entry_id), "username": username},
            {"$set": {"sentiment": new_sentiment}}
        )
        
        return jsonify({
            "message": "Sentiment updated successfully!",
            "id": entry_id,
            "new_sentiment": new_sentiment
        }), 200
    except Exception as e:
        print(f"Error updating sentiment for entry {entry_id}: {e}")
        return jsonify({"error": f"Failed to update sentiment: {e}"}), 500

# --- Endpoint for Time-Series Sentiment Trends ---
@app.route('/journal/sentiment_trends/<username>', methods=['GET'])
def get_sentiment_trends(username):
    """
    Endpoint to retrieve sentiment trends over time for a specific user.
    Returns daily counts of positive, negative, neutral, mixed, and unknown sentiments.
    """
    if db is None: # Check if DB connection failed at startup
        return jsonify({"error": "Database connection not available"}), 500

    try:
        pipeline = [
            {"$match": {"username": username}},
            {"$project": {
                "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                "sentiment": {"$ifNull": ["$sentiment", "unknown"]} # Handle missing sentiment
            }},
            {"$group": {
                "_id": {"date": "$date", "sentiment": "$sentiment"},
                "count": {"$sum": 1}
            }},
            {"$group": {
                "_id": "$_id.date",
                "sentiments": {
                    "$push": {
                        "sentiment": "$_id.sentiment",
                        "count": "$count"
                    }
                }
            }},
            {"$sort": {"_id": 1}} # Sort by date ascending
        ]
        
        trends_cursor = db.journal_entries.aggregate(pipeline) # NOW uses db.journal_entries
        
        # Format data for charting: { date: "YYYY-MM-DD", positive: X, negative: Y, ... }
        formatted_trends = []
        for day_data in trends_cursor:
            date_str = day_data['_id']
            daily_counts = {
                "date": date_str,
                "positive": 0,
                "neutral": 0,
                "negative": 0,
                "mixed": 0,
                "unknown": 0
            }
            for sentiment_item in day_data['sentiments']:
                sentiment_type = sentiment_item['sentiment']
                count = sentiment_item['count']
                if sentiment_type in daily_counts:
                    daily_counts[sentiment_type] = count
                else:
                    daily_counts['unknown'] += count # Fallback for unexpected sentiment types
            formatted_trends.append(daily_counts)
        
        return jsonify(formatted_trends), 200
    except Exception as e:
        print(f"Error getting sentiment trends: {e}")
        return jsonify({"error": f"Failed to retrieve sentiment trends: {e}"}), 500

# --- Endpoint for Generating Journaling Prompts ---
@app.route('/journal/generate_prompt/<username>', methods=['POST'])
def generate_journal_prompt(username):
    """
    Endpoint to generate a personalized journaling prompt based on recent entries.
    """
    try:
        if db is None: # Check if DB connection failed at startup
            return jsonify({"error": "Database connection not available"}), 500
        # Fetch recent entries for context (e.g., last 5 entries)
        recent_entries_cursor = db.journal_entries.find({"username": username}).sort("timestamp", -1).limit(5) # NOW uses db.journal_entries
        recent_entries_text = "\n".join([entry['text'] for entry in recent_entries_cursor])

        if not recent_entries_text:
            # If no recent entries, provide a general prompt
            prompt_context = "The user has no recent journal entries."
        else:
            prompt_context = f"The user's recent journal entries include:\n{recent_entries_text}"

        llm_prompt = f"""Based on the following context about the user's recent journal entries, suggest a single, concise, and encouraging journaling prompt. The prompt should help the user reflect further on their well-being, emotions, or experiences. Keep it to one sentence.

        Context:
        {prompt_context}

        Journaling Prompt:"""

        payload = {
            "contents": [{"role": "user", "parts": [{"text": llm_prompt}]}],
            "generationConfig": {
                "temperature": 0.8, # Slightly higher temperature for more creative prompts
                "maxOutputTokens": 100
            }
        }

        headers = {
            'Content-Type': 'application/json'
        }
        
        # This line correctly uses the GEMINI_API_KEY from the environment variable
        GEMINI_API_URL_WITH_KEY = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"

        response = requests.post(GEMINI_API_URL_WITH_KEY, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        
        gemini_response = response.json()
        
        if gemini_response and gemini_response.get('candidates'):
            generated_prompt = gemini_response['candidates'][0]['content']['parts'][0]['text'].strip()
            return jsonify({"prompt": generated_prompt}), 200
        else:
            return jsonify({"error": "Failed to generate a journaling prompt from LLM."}), 500

    except requests.exceptions.HTTPError as e:
        print(f"Error calling Gemini API for prompt generation: {e.response.status_code} - {e.response.text}")
        return jsonify({"error": f"Failed to generate prompt (HTTP Error): {e.response.status_code}"}), 500
    except requests.exceptions.RequestException as e:
        print(f"Network error calling Gemini API for prompt generation: {e}")
        return jsonify({"error": f"Failed to generate prompt (Network Error): {e}"}), 500
    except Exception as e:
        print(f"Unexpected error in prompt generation: {e}")
        return jsonify({"error": f"An unexpected error occurred during prompt generation: {e}"}), 500

# --- Endpoint for Period Summary with Narrative ---
@app.route('/journal/period_summary/<username>', methods=['POST'])
def get_period_summary(username):
    """
    Endpoint to generate a narrative summary of journal entries for a given period.
    Expects JSON: {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}
    """
    data = request.get_json()
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')

    if not start_date_str or not end_date_str:
        return jsonify({"error": "Start date and end date are required."}), 400
    
    if db is None: # Check if DB connection failed at startup
        return jsonify({"error": "Database connection not available"}), 500

    try:
        # Convert date strings to datetime objects
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        # To include entries on the end_date, set its time to the end of the day
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Fetch entries for the specified user and date range
        entries_cursor = db.journal_entries.find({ # NOW uses db.journal_entries
            "username": username,
            "timestamp": {"$gte": start_date, "$lte": end_date}
        }).sort("timestamp", 1) # Sort by date ascending for chronological summary

        all_entries_text = ""
        entry_count = 0
        for entry in entries_cursor:
            all_entries_text += f"Date: {entry['date_display']}\nEntry: {entry['text']}\n\n"
            entry_count += 1

        if not all_entries_text:
            return jsonify({"summary": "No journal entries found for the selected period."}), 200

        llm_prompt = f"""Summarize the following journal entries from a user over a specific period. Focus on identifying key themes, recurring emotions, significant events, and overall well-being trends. Provide a compassionate and insightful narrative summary, highlighting any notable changes or patterns. Keep the summary concise, under 250 words.

        Journal Entries for the period:
        {all_entries_text}

        Period Summary:"""

        payload = {
            "contents": [{"role": "user", "parts": [{"text": llm_prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 300 # Increased max tokens for a more comprehensive summary
            }
        }

        headers = {
            'Content-Type': 'application/json'
        }
        
        # This line correctly uses the GEMINI_API_KEY from the environment variable
        GEMINI_API_URL_WITH_KEY = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"

        response = requests.post(GEMINI_API_URL_WITH_KEY, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        
        gemini_response = response.json()
        
        if gemini_response and gemini_response.get('candidates'):
            generated_summary = gemini_response['candidates'][0]['content']['parts'][0]['text'].strip()
            return jsonify({"summary": generated_summary, "entry_count": entry_count}), 200
        else:
            return jsonify({"error": "Failed to generate a period summary from LLM."}), 500

    except ValueError:
        return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD."}), 400 # Fixed line
    except requests.exceptions.HTTPError as e:
        print(f"Error calling Gemini API for period summary: {e.response.status_code} - {e.response.text}")
        return jsonify({"error": f"Failed to generate period summary (HTTP Error): {e.response.status_code}"}), 500
    except requests.exceptions.RequestException as e:
        print(f"Network error calling Gemini API for period summary: {e}")
        return jsonify({"error": f"Failed to generate period summary (Network Error): {e}"}), 500
    except Exception as e:
        print(f"Unexpected error in period summary generation: {e}")
        return jsonify({"error": f"An unexpected error occurred during period summary generation: {e}"}), 500

if __name__ == '__main__':
    # This block is for local development only.
    # When deploying to Render, Gunicorn or another WSGI server will run the app.
    app.run(debug=True)
