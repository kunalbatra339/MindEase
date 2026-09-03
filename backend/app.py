from flask import Flask, jsonify, request
from flask_cors import CORS # Keep CORS
from datetime import datetime
import os
import requests
import json
import joblib
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from pymongo import MongoClient # Import MongoClient directly
from dotenv import load_dotenv
load_dotenv()
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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent"


# ============================================================
# Custom ML Emotion Model
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.abspath(
    os.path.join(
        BASE_DIR,
        "..",
        "ml",
        "models",
        "emotion_model.pkl"
    )
)

try:
    emotion_model = joblib.load(MODEL_PATH)
    print(f"Custom emotion model loaded successfully from: {MODEL_PATH}")
except Exception as e:
    emotion_model = None
    print(f"Error loading custom emotion model: {e}")


# ============================================================
# Custom ML Emotion Prediction
# ============================================================

LABEL_NAMES = [
    "sadness",
    "joy",
    "love",
    "anger",
    "fear",
    "surprise"
]


def predict_emotion(text):
    """
    Predict the emotion expressed in a journal entry
    using the custom-trained TF-IDF + calibrated SVM model.

    Returns:
        {
            "emotion": <predicted emotion>,
            "confidence": <prediction confidence>
        }
    """

    if emotion_model is None:
        raise RuntimeError("Emotion model is not loaded.")

    # Model prediction
    prediction = emotion_model.predict([text])[0]

    # Model probabilities
    probabilities = emotion_model.predict_proba([text])[0]

    # Convert predicted numeric label into emotion name
    emotion = LABEL_NAMES[int(prediction)]

    # Probability corresponding to predicted emotion
    confidence = float(probabilities[int(prediction)])

    return {
        "emotion": emotion,
        "confidence": confidence
    }



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
    data = request.get_json(silent=True) or {}
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
    data = request.get_json(silent=True) or {}
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
    data = request.get_json(silent=True) or {}
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
    Endpoint to add a new journal entry for a specific user.

    The custom ML model predicts the emotional state and confidence.

    Expects JSON:
    {"text": "Your journal entry here"}
    """

    data = request.get_json()

    if not data or 'text' not in data:
        return jsonify({
            "error": "Missing 'text' field in request"
        }), 400

    if db is None:
        return jsonify({
            "error": "Database connection not available"
        }), 500

    entry_text = data['text']

    if not isinstance(entry_text, str) or not entry_text.strip():
        return jsonify({
            "error": "Journal text must be a non-empty string"
        }), 400

    entry_text = entry_text.strip()
    timestamp = datetime.now()

    # ========================================================
    # CUSTOM ML EMOTION CLASSIFICATION
    # ========================================================

    emotion_result = predict_emotion(entry_text)

    emotion = emotion_result["emotion"]
    emotion_confidence = emotion_result["confidence"]

    print(
        f"ML emotion for entry: "
        f"'{entry_text[:30]}...' is "
        f"'{emotion}' "
        f"(confidence: {emotion_confidence:.4f})"
    )

    # ========================================================
    # JOURNAL ENTRY
    # ========================================================

    journal_entry = {
        "text": entry_text,
        "timestamp": timestamp,
        "date_display": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "username": username,

        # Custom ML emotion fields
        "emotion": emotion,
        "emotion_confidence": emotion_confidence
    }

    try:

        result = db.journal_entries.insert_one(
            journal_entry
        )

        return jsonify({
            "message": "Journal entry added successfully!",
            "id": str(result.inserted_id),

            "entry": {
                "id": str(result.inserted_id),
                "text": entry_text,
                "date": journal_entry["date_display"],
                "emotion": emotion,
                "emotion_confidence": emotion_confidence
            }
        }), 201

    except Exception as e:

        return jsonify({
            "error": f"Failed to save journal entry: {e}"
        }), 500

@app.route('/journal/<username>', methods=['GET'])
def get_journal_entries(username):
    """
    Endpoint to retrieve all journal entries for a specific user.
    Returns a list of journal entries, sorted by timestamp descending.
    """

    if db is None:
        return jsonify({
            "error": "Database connection not available"
        }), 500

    try:
        entries_cursor = db.journal_entries.find(
            {"username": username}
        ).sort(
            "timestamp",
            -1
        )

        entries = []

        for entry in entries_cursor:
            entries.append({
                "id": str(entry['_id']),
                "text": entry['text'],
                "date": entry['date_display'],
                "emotion": entry.get('emotion', 'unknown'),
                "emotion_confidence": entry.get(
                    'emotion_confidence',
                    0
                )
            })

        return jsonify(entries), 200

    except Exception as e:
        return jsonify({
            "error": f"Failed to retrieve journal entries: {e}"
        }), 500

@app.route('/journal/insight', methods=['POST'])
def get_journal_insight():
    """
    Endpoint to get an LLM-generated insight for a journal entry.
    Expects JSON: {"text": "The journal entry text"}
    """
    print("\n--- Insight Request Received ---")
    data = request.get_json(silent=True) or {}
    
    if 'text' not in data:
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
    "contents": [
        {
            "role": "user",
            "parts": [{"text": prompt}]
        }
    ],
    "generationConfig": {
        "maxOutputTokens": 500,
        "thinkingConfig": {
            "thinkingLevel": "minimal"
        }
    }
}

    headers = {
        'Content-Type': 'application/json'
    }
    
    # This line correctly uses the GEMINI_API_KEY from the environment variable
    GEMINI_API_URL_WITH_KEY = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"

    try:
        print(f"Attempting call to Gemini API: {GEMINI_API_URL}")
        response = requests.post(GEMINI_API_URL_WITH_KEY, headers=headers, data=json.dumps(payload), timeout=60)
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

# --- Endpoint for Emotion Summary ---
@app.route('/journal/sentiment_summary/<username>', methods=['GET'])
def get_sentiment_summary(username):
    """
    Endpoint to retrieve a summary of emotion counts for a specific user.
    Uses the custom ML emotion classification.
    """

    if db is None:
        return jsonify({"error": "Database connection not available"}), 500

    try:
        pipeline = [
            {"$match": {"username": username}},
            {"$group": {
                "_id": "$emotion",
                "count": {"$sum": 1}
            }}
        ]

        emotions_cursor = db.journal_entries.aggregate(pipeline)

        summary = {
            "joy": 0,
            "sadness": 0,
            "anger": 0,
            "fear": 0,
            "love": 0,
            "surprise": 0,
            "unknown": 0,
            "total": 0
        }

        for item in emotions_cursor:
            emotion_type = item['_id'] if item['_id'] else 'unknown'
            count = item['count']

            if emotion_type in summary:
                summary[emotion_type] = count
            else:
                summary['unknown'] += count

            summary['total'] += count

        return jsonify(summary), 200

    except Exception as e:
        print(f"Error getting emotion summary: {e}")
        return jsonify({
            "error": f"Failed to retrieve emotion summary: {e}"
        }), 500



# --- Endpoint for Time-Series Emotion Trends ---
@app.route('/journal/sentiment_trends/<username>', methods=['GET'])
def get_sentiment_trends(username):
    """
    Endpoint to retrieve emotion trends over time for a specific user.
    Uses the custom ML emotion classification.
    """

    if db is None:
        return jsonify({"error": "Database connection not available"}), 500

    try:
        pipeline = [
            {"$match": {"username": username}},

            {"$project": {
                "date": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$timestamp"
                    }
                },
                "emotion": {
                    "$ifNull": ["$emotion", "unknown"]
                }
            }},

            {"$group": {
                "_id": {
                    "date": "$date",
                    "emotion": "$emotion"
                },
                "count": {"$sum": 1}
            }},

            {"$group": {
                "_id": "$_id.date",
                "emotions": {
                    "$push": {
                        "emotion": "$_id.emotion",
                        "count": "$count"
                    }
                }
            }},

            {"$sort": {"_id": 1}}
        ]

        trends_cursor = db.journal_entries.aggregate(pipeline)

        formatted_trends = []

        for day_data in trends_cursor:

            date_str = day_data['_id']

            daily_counts = {
                "date": date_str,
                "joy": 0,
                "sadness": 0,
                "anger": 0,
                "fear": 0,
                "love": 0,
                "surprise": 0,
                "unknown": 0
            }

            for emotion_item in day_data['emotions']:

                emotion_type = emotion_item['emotion']
                count = emotion_item['count']

                if emotion_type in daily_counts:
                    daily_counts[emotion_type] = count
                else:
                    daily_counts['unknown'] += count

            formatted_trends.append(daily_counts)

        return jsonify(formatted_trends), 200

    except Exception as e:
        print(f"Error getting emotion trends: {e}")

        return jsonify({
            "error": f"Failed to retrieve emotion trends: {e}"
        }), 500

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
                "maxOutputTokens": 200,
                "thinkingConfig": {
                    "thinkingLevel": "minimal"
                }
            }
        }

        headers = {
            'Content-Type': 'application/json'
        }
        
        # This line correctly uses the GEMINI_API_KEY from the environment variable
        GEMINI_API_URL_WITH_KEY = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"

        response = requests.post(GEMINI_API_URL_WITH_KEY, headers=headers, data=json.dumps(payload), timeout=60)
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
    Generate a narrative summary of a user's journal entries
    for a selected date range.

    Expects JSON:
    {
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD"
    }
    """

    print("\n========================================")
    print("PERIOD SUMMARY REQUEST")
    print("========================================")

    # ---------------------------------------------------------
    # 1. Validate request data
    # ---------------------------------------------------------
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body is missing."
        }), 400

    start_date_str = data.get("start_date")
    end_date_str = data.get("end_date")

    if not start_date_str or not end_date_str:
        return jsonify({
            "error": "Start date and end date are required."
        }), 400

    print(f"Username: {username}")
    print(f"Start Date: {start_date_str}")
    print(f"End Date: {end_date_str}")

    # ---------------------------------------------------------
    # 2. Check MongoDB
    # ---------------------------------------------------------
    if db is None:
        return jsonify({
            "error": "Database connection not available"
        }), 500

    try:

        # -----------------------------------------------------
        # 3. Convert dates
        # -----------------------------------------------------
        start_date = datetime.strptime(
            start_date_str,
            "%Y-%m-%d"
        )

        end_date = datetime.strptime(
            end_date_str,
            "%Y-%m-%d"
        )

        # Include the complete end date
        end_date = end_date.replace(
            hour=23,
            minute=59,
            second=59,
            microsecond=999999
        )

        print(f"MongoDB range: {start_date} -> {end_date}")

        # -----------------------------------------------------
        # 4. Fetch journal entries
        # -----------------------------------------------------
        entries_cursor = db.journal_entries.find(
            {
                "username": username,
                "timestamp": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }
        ).sort(
            "timestamp",
            1
        )

        # -----------------------------------------------------
        # 5. Build clean context for Gemini
        # -----------------------------------------------------
        journal_entries = []
        entry_count = 0

        for entry in entries_cursor:

            text = entry.get("text", "").strip()

            if not text:
                continue

            emotion = entry.get(
                "emotion",
                "unknown"
            )

            confidence = entry.get(
                "emotion_confidence",
                None
            )

            date_display = entry.get(
                "date_display",
                str(entry.get("timestamp", ""))
            )

            journal_entries.append(
                f"Date: {date_display}\n"
                f"Emotion: {emotion}\n"
                f"Entry: {text}"
            )

            entry_count += 1

        print(f"Entries found: {entry_count}")

        # -----------------------------------------------------
        # 6. No entries
        # -----------------------------------------------------
        if entry_count == 0:

            print("No journal entries found.")

            return jsonify({
                "summary": "No journal entries found for the selected period.",
                "entry_count": 0
            }), 200

        # -----------------------------------------------------
        # 7. Combine entries
        # -----------------------------------------------------
        all_entries_text = "\n\n".join(
            journal_entries
        )

        print("\nJournal context sent to Gemini:")
        print("----------------------------------------")
        print(all_entries_text)
        print("----------------------------------------")

        # -----------------------------------------------------
        # 8. Gemini prompt
        # -----------------------------------------------------
        llm_prompt = f"""
You are analyzing a user's personal journal.

Write ONE concise, compassionate narrative summary of the
journal entries provided below.

Your summary should:

- Describe the main emotions expressed.
- Identify important recurring themes or experiences.
- Mention noticeable emotional patterns or changes.
- Briefly describe the user's overall emotional state.
- Be supportive and non-judgmental.
- Avoid diagnosing the user.
- Do not give medical advice.
- Do not mention that you are an AI.
- Do not refer to "the prompt", "the context", or "the entries".
- Do not include headings.
- Do not use bullet points.
- Do not include labels such as "Summary:".
- Do not include analysis outside the summary.
- Return ONLY the final narrative paragraph.
- Keep it between 60 and 150 words.

Journal entries:

{all_entries_text}

Now write ONLY the final narrative summary.
"""

        # -----------------------------------------------------
        # 9. Gemini request payload
        # -----------------------------------------------------
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": llm_prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 300,
                "thinkingConfig": {
                    "thinkingLevel": "minimal"
                }
            }
        }

        headers = {
            "Content-Type": "application/json"
        }

        GEMINI_API_URL_WITH_KEY = (
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
        )

        print("\nCalling Gemini API...")
        print(
            f"Model URL: {GEMINI_API_URL_WITH_KEY.split('?')[0]}"
        )

        # -----------------------------------------------------
        # 10. Call Gemini
        # -----------------------------------------------------
        response = requests.post(
            GEMINI_API_URL_WITH_KEY,
            headers=headers,
            data=json.dumps(payload),
            timeout=60
        )

        print(
            f"Gemini HTTP Status: {response.status_code}"
        )

        response.raise_for_status()

        gemini_response = response.json()

        # -----------------------------------------------------
        # 11. PRINT RAW RESPONSE
        # -----------------------------------------------------
        print("\nGEMINI RAW PERIOD SUMMARY RESPONSE:")
        print("----------------------------------------")
        print(
            json.dumps(
                gemini_response,
                indent=2
            )
        )
        print("----------------------------------------")

        # -----------------------------------------------------
        # 12. Validate candidates
        # -----------------------------------------------------
        candidates = gemini_response.get(
            "candidates",
            []
        )

        if not candidates:

            print(
                "Gemini returned no candidates."
            )

            return jsonify({
                "error": "Gemini returned no candidates."
            }), 500

        candidate = candidates[0]

        # -----------------------------------------------------
        # 13. Check candidate content
        # -----------------------------------------------------
        content = candidate.get(
            "content",
            {}
        )

        parts = content.get(
            "parts",
            []
        )

        if not parts:

            print(
                "Gemini candidate contains no parts."
            )

            print(
                "Finish reason:",
                candidate.get("finishReason")
            )

            return jsonify({
                "error": (
                    "Gemini returned no text content "
                    "for the period summary."
                )
            }), 500

        # -----------------------------------------------------
        # 14. Extract ALL text parts safely
        # -----------------------------------------------------
        text_parts = []

        for part in parts:

            if isinstance(part, dict):

                part_text = part.get(
                    "text"
                )

                if part_text:
                    text_parts.append(
                        part_text
                    )

        generated_summary = "\n".join(
            text_parts
        ).strip()

        # -----------------------------------------------------
        # 15. Validate generated text
        # -----------------------------------------------------
        if not generated_summary:

            print(
                "Gemini returned parts but no text."
            )

            return jsonify({
                "error": (
                    "Gemini returned an empty "
                    "period summary."
                )
            }), 500

        # -----------------------------------------------------
        # 16. Clean accidental formatting
        # -----------------------------------------------------
        generated_summary = generated_summary.strip()

        if generated_summary.startswith(
            "Summary:"
        ):
            generated_summary = (
                generated_summary[
                    len("Summary:"):
                ].strip()
            )

        # -----------------------------------------------------
        # 17. Log final result
        # -----------------------------------------------------
        print("\nFINAL PERIOD SUMMARY:")
        print("----------------------------------------")
        print(generated_summary)
        print("----------------------------------------")

        # -----------------------------------------------------
        # 18. Return to React
        # -----------------------------------------------------
        return jsonify({
            "summary": generated_summary,
            "entry_count": entry_count
        }), 200

    # ---------------------------------------------------------
    # Date errors
    # ---------------------------------------------------------
    except ValueError:

        print(
            "Invalid date format received."
        )

        return jsonify({
            "error": (
                "Invalid date format. "
                "Please use YYYY-MM-DD."
            )
        }), 400

    # ---------------------------------------------------------
    # Gemini HTTP errors
    # ---------------------------------------------------------
    except requests.exceptions.HTTPError as e:

        status_code = (
            e.response.status_code
            if e.response is not None
            else 500
        )

        response_text = (
            e.response.text
            if e.response is not None
            else str(e)
        )

        print(
            "\nGEMINI HTTP ERROR:"
        )
        print(
            f"Status: {status_code}"
        )
        print(
            response_text
        )

        return jsonify({
            "error": (
                "Failed to generate period summary "
                f"(HTTP Error): {status_code}"
            )
        }), 500

    # ---------------------------------------------------------
    # Network errors
    # ---------------------------------------------------------
    except requests.exceptions.RequestException as e:

        print(
            "\nGEMINI NETWORK ERROR:"
        )
        print(
            str(e)
        )

        return jsonify({
            "error": (
                "Failed to generate period summary "
                f"(Network Error): {e}"
            )
        }), 500

    # ---------------------------------------------------------
    # Any other error
    # ---------------------------------------------------------
    except Exception as e:

        print(
            "\nUNEXPECTED PERIOD SUMMARY ERROR:"
        )
        print(
            repr(e)
        )

        return jsonify({
            "error": (
                "An unexpected error occurred during "
                f"period summary generation: {e}"
            )
        }), 500

if __name__ == '__main__':
    # This block is for local development only.
    # When deploying to Render, Gunicorn or another WSGI server will run the app.
    app.run(debug=True)