import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
import traceback
from datetime import datetime
import pytz

app = Flask(__name__)
CORS(app)

# --- Google Sheetsの設定 ---
SERVICE_ACCOUNT_FILE_PATH = '/etc/secrets/service_account.json'
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
SHEET_NAME_COUNT = 'レジ待ち台数'
SHEET_NAME_WAIT_TIME = 'レジ待ち時間'
SHEET_NAME_LOG = 'スクリプトのログ' 
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

# ★★★★★ 追加：完了した取引の履歴をサーバーのメモリ上で保持 ★★★★★
# 注意：このリストはサーバーが再起動するとリセットされます。
completed_transactions = []

# --- ヘルパー関数 ---
def get_spreadsheet_client():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE_PATH, scopes=SCOPES)
    return gspread.authorize(creds)

def get_worksheet(spreadsheet, sheet_name, headers=None):
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=100, cols=20)
        if headers:
            worksheet.append_row(headers)
        return worksheet

def log_event(client, message):
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        log_sheet = get_worksheet(spreadsheet, SHEET_NAME_LOG, headers=['タイムスタンプ', 'サーバー名', 'イベント'])
        jst = pytz.timezone('Asia/Tokyo')
        timestamp = datetime.now(jst).strftime('%Y/%m/%d %H:%M:%S')
        log_sheet.append_row([timestamp, 'sheet-writer', message])
    except Exception as e:
        print(f"ロギングエラー: {e}")

# --- APIエンドポイント ---

@app.route('/write', methods=['POST'])
def write_count():
    data = request.get_json()
    timestamp = data.get('timestamp')
    employee_count = data.get('employeeCount')
    
    client = get_spreadsheet_client()
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = get_worksheet(spreadsheet, SHEET_NAME_COUNT, headers=['更新時間', '従業員チェック台数'])
        worksheet.append_row([timestamp, employee_count])
        
        log_event(client, f"台数記録成功: {employee_count}人")
        return jsonify({"status": "success"}), 200
    except Exception:
        log_event(client, f"台数記録エラー: {traceback.format_exc()}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/log-wait-time', methods=['POST'])
def log_wait_time():
    data = request.get_json()
    client = get_spreadsheet_client()
    try:
        time_format = '%Y/%m/%d %H:%M:%S'
        start_time_obj = datetime.strptime(data['startTime'], time_format)
        end_time_obj = datetime.strptime(data['endTime'], time_format)

        # 1. 完了した取引として履歴に追加
        transaction = {
            'terminalId': data['terminalId'],
            'startTime': start_time_obj,
            'endTime': end_time_obj
        }
        completed_transactions.append(transaction)

        # 2. Single Lane Formulaの計算
        r_i = len(completed_transactions)
        b_ai = sum(1 for t in completed_transactions if t['endTime'] < start_time_obj)
        
        queue_len_formula = r_i - b_ai - 1
        queue_len_formula = max(queue_len_formula, 0) # 負の値にならないように調整

        # 3. スプレッドシートへの書き込み
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        # ★★★★★ 変更点：ヘッダーを元のシンプルな形式に戻す ★★★★★
        headers = [
            'ターミナルID', '開始時刻', '終了時刻', '終了ステータス', 
            'レジ待ち台数', '総数量', 'レジ待ち時間（秒）'
        ]
        worksheet = get_worksheet(spreadsheet, SHEET_NAME_WAIT_TIME, headers=headers)
        
        wait_duration = round((end_time_obj - start_time_obj).total_seconds())

        # ★★★★★ 変更点：書き込む行のデータを修正 ★★★★★
        worksheet.append_row([
            data['terminalId'], data['startTime'], data['endTime'], data['endStatus'],
            queue_len_formula, # Single Lane Formulaで計算した待ち人数
            data.get('totalItems'), 
            wait_duration
        ])
        
        log_event(client, f"待ち時間記録成功: ターミナルID {data['terminalId']}")
        return jsonify({"status": "success"}), 200
    except Exception:
        log_event(client, f"待ち時間記録エラー: {traceback.format_exc()}")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    app.run(port=int(os.environ.get('PORT', 8080)))
