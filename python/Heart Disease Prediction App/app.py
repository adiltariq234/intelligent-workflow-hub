import streamlit as st
import pandas as pd
import joblib

# Page Config
st.set_page_config(
    page_title="Heart Disease Predictor",
    page_icon="❤️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>

.main{
    background: linear-gradient(135deg,#0f172a,#1e293b);
}

.hero{
    text-align:center;
    padding:20px;
    border-radius:20px;
    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(15px);
    margin-bottom:20px;
}

.hero h1{
    color:white;
    font-size:50px;
}

.hero p{
    color:#cbd5e1;
    font-size:18px;
}

.stButton>button{
    width:100%;
    background:linear-gradient(45deg,#ff416c,#ff4b2b);
    color:white;
    border:none;
    border-radius:12px;
    padding:12px;
    font-size:18px;
    font-weight:bold;
}

.metric-card{
    background: rgba(255,255,255,0.08);
    padding:20px;
    border-radius:20px;
    text-align:center;
}

</style>
""", unsafe_allow_html=True)

# Load Files
model = joblib.load("Random_heart.pkl")
scaler = joblib.load("scaler.pkl")
expected_columns = joblib.load("columns.pkl")

# Hero Section
st.markdown("""
<div class='hero'>
<h1>❤️ Heart Disease Predictor</h1>
<p>AI Powered Heart Risk Analysis System</p>
</div>
""", unsafe_allow_html=True)

# Layout
col1, col2 = st.columns(2)

with col1:
    age = st.slider("🎂 Age",18,100,40)
    sex = st.selectbox("👤 Gender",["M","F"])
    chest_pain = st.selectbox("💔 Chest Pain Type",["ATA","NAP","TA","ASY"])
    resting_bp = st.number_input("🩸 Blood Pressure",80,200,120)
    cholesterol = st.number_input("🥩 Cholesterol",100,600,200)

with col2:
    fasting_bs = st.selectbox("🍬 Fasting Blood Sugar",[0,1])
    resting_ecg = st.selectbox("📈 ECG Result",["Normal","ST","LVH"])
    max_hr = st.slider("❤️ Max Heart Rate",60,220,150)
    exercise_angina = st.selectbox("🏃 Exercise Angina",["Y","N"])
    oldpeak = st.slider("📉 Old Peak",0.0,6.0,1.0)
    st_slope = st.selectbox("📊 ST Slope",["Up","Flat","Down"])

if st.button("🚀 Analyze Heart Risk"):

    raw_input = {
        "Age": age,
        "RestingBP": resting_bp,
        "Cholesterol": cholesterol,
        "FastingBS": fasting_bs,
        "MaxHR": max_hr,
        "Oldpeak": oldpeak,
        "Sex_" + sex: 1,
        "ChestPainType_" + chest_pain: 1,
        "RestingECG_" + resting_ecg: 1,
        "ExerciseAngina_" + exercise_angina: 1,
        "ST_Slope_" + st_slope: 1
    }

    input_df = pd.DataFrame([raw_input])

    for col in expected_columns:
        if col not in input_df.columns:
            input_df[col] = 0

    input_df = input_df[expected_columns]

    scaled_input = scaler.transform(input_df)

    prediction = model.predict(scaled_input)[0]

    # Probability
    if hasattr(model, "predict_proba"):
        probability = model.predict_proba(scaled_input)[0][1]
    else:
        probability = 0.50

    st.markdown("---")

    if prediction == 1:
        st.error(f"⚠️ High Risk Detected ({probability*100:.1f}%)")
        st.progress(float(probability))

        st.markdown("""
        ### ❤️ Recommendations
        - Exercise regularly
        - Reduce cholesterol intake
        - Monitor blood pressure
        - Consult a cardiologist
        """)
    else:
        st.success(f"✅ Low Risk ({(1-probability)*100:.1f}%)")
        st.progress(float(1-probability))

        st.markdown("""
        ### 🌿 Healthy Lifestyle
        - Maintain balanced diet
        - Stay active
        - Regular checkups
        - Avoid smoking
        """)

st.markdown("---")
st.caption("Made with ❤️ by Adil Tariq")