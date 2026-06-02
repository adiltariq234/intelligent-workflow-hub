from flask import Flask, render_template, request
import joblib
import numpy as np
import requests
import os
from dotenv import load_dotenv

# .env file load karein (Yeh file templates folder se bahar main folder mein honi chahiye)
load_dotenv()

app = Flask(__name__)

# Absolute Path Setup (Taake Windows par file dhoondne ka masla na ho)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'nb_model.pkl')

# Model Load (joblib ke zariye jo Windows par invalid load key error nahi deta)
try:
    model = joblib.load(MODEL_PATH)
    print("Information: ML Model loaded successfully using Joblib!")
except Exception as e:
    print(f"Error loading model: {str(e)}")
    print("Tip: Agar error aaye to check karein aapka model 'nb_model.pkl' main folder mein maujood hai ya nahi.")

# OpenRouter API Key secure tarike se uthein
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "YOUR_OPENROUTER_API_KEY_HERE")

# 1. Home Route (Main Dashboard)
@app.route('/')
def home():
    return render_template("index.html")

# 2. Prediction Route
@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Form se saari numerical inputs ko float mein convert karke uthein
        form_values = list(request.form.values())
        features = [float(x) for x in form_values]
        final_features = np.array([features])

        # ML Prediction (Model se outcome check karein)
        prediction = model.predict(final_features)

        # Dataset Standard: 0 = Malignant (Cancerous), 1 = Benign (Non-cancerous)
        if prediction[0] == 0:
            result = "Malignant Cancer Detected"
        else:
            result = "Benign Tumor Detected"

        # AI Explanation Prompt (Aam user ki aasani ke liye)
        prompt = f"""
        A breast cancer prediction model predicted: {result}.
        Explain this result in simple language for a patient.
        Include:
        - Meaning of the prediction
        - Basic precautions
        - Reminder to consult an oncologist/doctor immediately.
        Keep response short, highly empathetic, and professional.
        """

        # OpenRouter API Call
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "openai/gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}]
        }

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10  # 10 seconds timeout taake app freeze na ho
        )

        # Safe API Handling
        if response.status_code == 200:
            response_data = response.json()
            if 'choices' in response_data:
                ai_response = response_data['choices'][0]['message']['content']
            else:
                ai_response = "AI explanation generation failed. Please check your OpenRouter API settings or credits."
        else:
            ai_response = f"Could not fetch AI explanation (API Status: {response.status_code}). Please refer to laboratory guidance."

        # Result ko wapas index.html par bhein
        return render_template(
            "index.html",
            prediction_text=result,
            ai_response=ai_response
        )

    except Exception as e:
        # Agar pure process mein koi error aaye to app crash na ho, balkay screen par error dikhe
        return render_template(
            "index.html",
            prediction_text="Diagnostic Processing Error",
            ai_response=f"Technical Stacktrace: {str(e)}"
        )

if __name__ == "__main__":
    # Development ke liye debug=True, port 5000 standard hai
    app.run(debug=True, port=5000)