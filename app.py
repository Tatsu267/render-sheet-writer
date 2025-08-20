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
SERVICE_ACCOUNT_FILE_PATH = '/etc/secrets/alien-isotope-455823-n4-6db6b2ed6b17.json'
SPREADSHEET_ID = '1wP2JQNj2iWTxq68XBzkg_Mb7uZtCC9_6f73G89Ds4Qw'
SHEET_NAME_COUNT = 'レジ待ち台数'
SHEET_NAME_WAIT_TIME = 'レジ待ち時間'
SHEET_NAME_LOG = 'スクリプトのログ' 
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

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
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = get_worksheet(spreadsheet, SHEET_NAME_WAIT_TIME, headers=['ターミナルID', '開始時刻', '終了時刻', '終了ステータス', 'レジ待ち台数', '総数量', 'レジ待ち時間（秒）'])
        
        start_time = datetime.strptime(data['startTime'], '%Y/%m/%d %H:%M:%S')
        end_time = datetime.strptime(data['endTime'], '%Y/%m/%d %H:%M:%S')
        wait_duration = round((end_time - start_time).total_seconds())
        waiting_line = int(data['startCount']) - 1 if data.get('startCount') and int(data['startCount']) > 0 else 0

        worksheet.append_row([
            data['terminalId'], data['startTime'], data['endTime'], data['endStatus'],
            waiting_line, data.get('totalItems'), wait_duration
        ])
        
        log_event(client, f"待ち時間記録成功: ターミナルID {data['terminalId']}")
        return jsonify({"status": "success"}), 200
    except Exception:
        log_event(client, f"待ち時間記録エラー: {traceback.format_exc()}")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    app.run(port=int(os.environ.get('PORT', 8080)))
