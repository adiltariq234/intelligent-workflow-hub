import streamlit as st
import pandas as pd
import joblib

st.set_page_config(page_title="Telco Churn Predictor", page_icon="📞", layout="centered")
st.title("📞 Telco Customer Churn Prediction")
st.markdown("**Kya customer churn karega? Prediction karo**")

# Load Model
@st.cache_resource
def load_model():
    return joblib.load('churn_decision_tree_model.pkl')
model = load_model()

# ====================== INPUTS ======================
col1, col2 = st.columns(2)

with col1:
    gender = st.selectbox("Gender", ["Female", "Male"])
    senior = st.selectbox("Senior Citizen", ["No", "Yes"])
    partner = st.selectbox("Partner", ["No", "Yes"])
    dependents = st.selectbox("Dependents", ["No", "Yes"])
    tenure = st.slider("Tenure (Months)", 0, 72, 12)
    phoneservice = st.selectbox("Phone Service", ["No", "Yes"])
    multiplelines = st.selectbox("Multiple Lines", ["No", "Yes", "No phone service"])
    internetservice = st.selectbox("Internet Service", ["DSL", "Fiber optic", "No"])

with col2:
    onlinesecurity = st.selectbox("Online Security", ["No", "Yes", "No internet service"])
    onlinebackup = st.selectbox("Online Backup", ["No", "Yes", "No internet service"])
    deviceprotection = st.selectbox("Device Protection", ["No", "Yes", "No internet service"])
    techsupport = st.selectbox("Tech Support", ["No", "Yes", "No internet service"])
    streamingtv = st.selectbox("Streaming TV", ["No", "Yes", "No internet service"])
    streamingmovies = st.selectbox("Streaming Movies", ["No", "Yes", "No internet service"])
    contract = st.selectbox("Contract", ["Month-to-month", "One year", "Two year"])
    paperless = st.selectbox("Paperless Billing", ["No", "Yes"])
    payment = st.selectbox("Payment Method", [
        "Electronic check", "Mailed check", 
        "Bank transfer (automatic)", "Credit card (automatic)"
    ])
    monthlycharges = st.number_input("Monthly Charges ($)", 18.0, 150.0, 70.0)

# ====================== PREDICTION ======================
if st.button("🔮 Predict Churn", type="primary", use_container_width=True):
    
    # Create DataFrame
    input_data = pd.DataFrame({
        'gender': [gender],
        'SeniorCitizen': [senior],
        'Partner': [partner],
        'Dependents': [dependents],
        'tenure': [tenure],
        'PhoneService': [phoneservice],
        'MultipleLines': [multiplelines],
        'InternetService': [internetservice],
        'OnlineSecurity': [onlinesecurity],
        'OnlineBackup': [onlinebackup],
        'DeviceProtection': [deviceprotection],
        'TechSupport': [techsupport],
        'StreamingTV': [streamingtv],
        'StreamingMovies': [streamingmovies],
        'Contract': [contract],
        'PaperlessBilling': [paperless],
        'PaymentMethod': [payment],
        'MonthlyCharges': [monthlycharges],
        'TotalCharges': [monthlycharges * max(tenure, 1)]
    })

    # One-hot encoding (same as training)
    input_encoded = pd.get_dummies(input_data, drop_first=True)

    # Important: Model ke saath features align karo
    # (Agar training mein kuch columns the jo yahan nahi hain)
    model_features = model.feature_names_in_ if hasattr(model, 'feature_names_in_') else None
    
    if model_features is not None:
        for col in model_features:
            if col not in input_encoded.columns:
                input_encoded[col] = 0
        input_encoded = input_encoded[model_features]

    # Prediction
    pred = model.predict(input_encoded)[0]
    prob = model.predict_proba(input_encoded)[0][1]

    st.divider()
    if pred == 1:
        st.error(f"⚠️ **High Risk** - Customer Churn Karega")
        st.write(f"**Probability**: {prob:.2%}")
    else:
        st.success(f"✅ **Low Risk** - Customer Nahi Churn Karega")
        st.write(f"**Probability**: {prob:.2%}")
    
    st.progress(float(prob))