from flask import Flask, render_template, request, Response
from flask import session
import sqlite3

def init_db():
    conn = sqlite3.connect('ethos.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT,
            category TEXT,
            risk INTEGER
        )
    ''')

    conn.commit()
    conn.close()

from blockchain_utils import (
    get_wallet_transfers, 
    process_analysis, 
    is_valid_ethereum_address
)
import io

app = Flask(__name__)
app.secret_key = "my_super_secret_key_123"

# Global variable to temporarily store data for export (for demo purposes)
last_analysis_df = None
@app.route('/', methods=['GET', 'POST'])
def index():
    global last_analysis_df

    if request.method == 'POST':
        address = request.form.get('wallet_address', '').strip()
        
        if not is_valid_ethereum_address(address):
            result = {"error": "Invalid Ethereum Address format."}
        else:
            raw_data = get_wallet_transfers(address)
            analysis = process_analysis(raw_data)
            transactions = raw_data[:10]
            
            if "df" in analysis:
                last_analysis_df = analysis.pop("df")
            
            result = analysis
            result["address"] = address
            result["transactions"] = transactions
            
            tx_count = result["count"]
            total_volume = result["volume"]
            asset_count = result["assets"]

            suspicious = False
            reason = ""

            if tx_count > 800 and asset_count <= 3:
                suspicious = True
                reason = "High transaction frequency with low asset diversity (Possible Bot)"

            elif total_volume > 100 and tx_count > 500:
                suspicious = True
                reason = "Very high trading volume detected"

            result["suspicious"] = suspicious
            result["reason"] = reason
            # Save to database

            conn = sqlite3.connect('ethos.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO history (address, category, risk) VALUES (?, ?, ?)",(address, result["category"], result["risk_score"]))
            conn.commit()
            conn.close()

            session['result'] = result   # SAVE HERE

    else:
        result = session.get('result')   # LOAD HERE

    return render_template("index.html", result=result)


@app.route('/download')
def download():
    """Route to download the analyzed transactions as a CSV."""
    global last_analysis_df
    if last_analysis_df is not None:
        proxy = io.StringIO()
        last_analysis_df.to_csv(proxy, index=False)
        return Response(
            proxy.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=ethos_analysis.csv"}
        )
    return "No data available", 404

# @app.route('/', methods=['GET','POST'])
# def home():
#     if request.method == 'POST':
#         wallet_address = request.form['wallet_address']
#         result = index(wallet_address)
#         session['result'] = result
#         print("SESSION AFTER SAVE:", session.get('result'))   # yaha

#     else:
#         result = session.get('result')
#         print("SESSION ON LOAD:", result)   #  yaha
#     return render_template('index.html', result=result)


@app.route('/wallet')
def wallet():
    return render_template('wallet.html', result=session.get('result'))

@app.route('/risk')
def risk():
    return render_template('risk.html', result=session.get('result'))

@app.route('/transactions')
def transactions():
    return render_template('transactions.html', result=session.get('result'))

@app.route('/history')
def history():
    conn = sqlite3.connect('ethos.db')
    cursor = conn.cursor()

    cursor.execute("SELECT category, COUNT(*) FROM history GROUP BY category")
    stats = cursor.fetchall()

    cursor.execute("SELECT address, category, risk FROM history ORDER BY id DESC LIMIT 10")
    data = cursor.fetchall()

    conn.close()

    return render_template('history.html', data=data, stats=stats)


init_db()

import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
    
