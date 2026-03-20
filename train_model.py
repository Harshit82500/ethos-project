import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

data = {
"transactions":[50,120,300,1000,20,80],
"volume":[2,5,20,1000,1,3],
"assets":[2,5,8,20,1,3],
"type":[
"Retail Trader",
"Retail Trader",
"Active Trader",
"Institutional Whale",
"Bot",
"Bot"
]
}

df = pd.DataFrame(data)

X = df[["transactions","volume","assets"]]
y = df["type"]

model = RandomForestClassifier()

model.fit(X,y)

joblib.dump(model,"wallet_model.pkl")

print("Model trained successfully")
