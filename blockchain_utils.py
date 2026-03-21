import requests
import os
import pandas as pd
import numpy as np
import re
import shap
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from dotenv import load_dotenv
from sklearn.ensemble import IsolationForest
import joblib

# Load model
model = joblib.load("wallet_model.pkl")

load_dotenv()

# API config
ALCHEMY_KEY = os.getenv("ALCHEMY_API_KEY")
ALCHEMY_URL = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}"


def is_valid_ethereum_address(address):
    pattern = re.compile(r'^0x[a-fA-F0-9]{40}$')
    return bool(pattern.match(address))


def get_wallet_transfers(wallet_address):
    payload = {
        "id": 1,
        "jsonrpc": "2.0",
        "method": "alchemy_getAssetTransfers",
        "params": [{
            "fromAddress": wallet_address,
            "category": ["external", "erc20"],
            "maxCount": "0x3E8"
        }]
    }

    try:
        response = requests.post(ALCHEMY_URL, json=payload)
        if response.status_code == 200:
            return response.json().get("result", {}).get("transfers", [])
        return []
    except Exception as e:
        print(f"API Error: {e}")
        return []


def calculate_risk_score(vol, cnt, assets):
    score = 0
    if vol > 1000:
        score += 40
    if cnt > 500:
        score += 30
    if assets < 2 and cnt > 10:
        score += 30
    return min(score, 100)


def process_analysis(transactions):

    # -------- EMPTY CASE --------
    if not transactions:
        return {
            "category": "New/Inactive Wallet",
            "volume": 0.0,
            "count": 0,
            "assets": 0,
            "risk_score": 0,
            "anomaly_count": 0,
            "shap_plot": None,
            "df": None
        }

    df = pd.DataFrame(transactions)

    # -------- SAFE VALUE COLUMN --------
    if 'value' not in df.columns:
        df['value'] = 0

    df['value'] = pd.to_numeric(df['value'], errors='coerce').fillna(0.0)

    # -------- SAFE ASSET COLUMN --------
    if 'asset' not in df.columns:
        df['asset'] = "UNKNOWN"

    # -------- ANOMALY DETECTION --------
    try:
        features = df[['value']]

        iso = IsolationForest(contamination=0.05, random_state=42)
        df['anomaly'] = iso.fit_predict(features)

    except Exception as e:
        print("Anomaly Error:", e)
        df['anomaly'] = 1  # default normal

    anomaly_count = int((df['anomaly'] == -1).sum())

    # -------- BASIC FEATURES --------
    vol = float(df['value'].sum())
    cnt = int(len(df))
    assets = int(df['asset'].nunique())

    # -------- SHAP EXPLAINABILITY --------
    shap_image = None

    try:
        X = pd.DataFrame([[cnt, vol, assets]],
        columns=["transactions", "volume", "assets"])

        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)

        plt.figure()

        if isinstance(shap_values, list):
            values = shap_values[0][0]
        else:
            values = shap_values[0]

        shap.bar_plot(values, feature_names=X.columns, show=False)

        plt.title("Feature Impact on Prediction")

        buf = BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)

        shap_image = base64.b64encode(buf.getvalue()).decode("utf-8")
        plt.close()

    except Exception as e:
        print("SHAP Error:", e)
        shap_image = None

    # -------- RULE-BASED LABEL --------
    if vol > 500:
        label = "Institutional Whale"
    elif cnt > 700:
        label = "High-Frequency Bot"
    elif assets > 10:
        label = "Diversified Collector"
    elif vol > 1:
        label = "Active Retail User"
    else:
        label = "Casual User"

    return {
        "category": label,
        "volume": round(vol, 2),
        "count": cnt,
        "assets": assets,
        "risk_score": calculate_risk_score(vol, cnt, assets),
        "anomaly_count": anomaly_count,
        "shap_plot": shap_image,
        "df": df  # keep for backend only
    }