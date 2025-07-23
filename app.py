from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
import traceback
from datetime import datetime

app = Flask(__name__)
CORS(app)

# --- Google Sheetsの設定 ---
SERVICE_ACCOUNT_FILE_PATH = '/etc/secrets/alien-isotope-455823-n4-6db6b2ed6b17.json'
SPREADSHEET_ID = '1wP2JQNj2iWTxq68XBzkg_Mb7uZtCC9_6f73G89Ds4Qw'
# --- 書き込むシート名を定義 ---
SHEET_NAME_COUNT = 'レジ待ち台数'
SHEET_NAME_WAIT_TIME = 'レジ待ち時間'
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

# --- ヘルパー関数：シートが存在しなければ作成 ---
def get_worksheet(spreadsheet, sheet_name):
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        # シートが存在しない場合は、ヘッダー付きで新規作成
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=100, cols=20)
        if sheet_name == SHEET_NAME_WAIT_TIME:
            worksheet.append_row(['ターミナルID', '開始時刻', '終了時刻', '終了ステータス', 'レジ待ち時間（秒）'])
        elif sheet_name == SHEET_NAME_COUNT:
             worksheet.append_row(['更新時間', '従業員チェック台数'])
        return worksheet

# --- APIエンドポイント ---

# 窓口A: 全体の台数を記録する (既存の機能)
@app.route('/write', methods=['POST'])
def write_count():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    timestamp = data.get('timestamp')
    employee_count = data.get('employeeCount')

    if timestamp is None or employee_count is None:
        return jsonify({"error": "Missing timestamp or employeeCount"}), 400

    try:
        creds = gspread.service_account(filename=SERVICE_ACCOUNT_FILE_PATH, scopes=SCOPES)
        spreadsheet = creds.open_by_key(SPREADSHEET_ID)
        worksheet = get_worksheet(spreadsheet, SHEET_NAME_COUNT)
        worksheet.append_row([timestamp, employee_count])
        
        print(f"台数記録成功: {timestamp}, {employee_count}")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"エラーが発生しました (write):\n{error_details}")
        return jsonify({"error": "Internal Server Error"}), 500

# 窓口B: 個別の待ち時間を記録する (新しい機能)
@app.route('/log-wait-time', methods=['POST'])
def log_wait_time():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    terminal_id = data.get('terminalId')
    start_time_str = data.get('startTime')
    end_time_str = data.get('endTime')
    end_status = data.get('endStatus')

    if not all([terminal_id, start_time_str, end_time_str, end_status]):
        return jsonify({"error": "Missing required data"}), 400

    try:
        # 文字列からdatetimeオブジェクトに変換
        time_format = '%Y/%m/%d %H:%M:%S'
        start_time = datetime.strptime(start_time_str, time_format)
        end_time = datetime.strptime(end_time_str, time_format)
        
        # 待ち時間を秒で計算
        wait_duration_seconds = (end_time - start_time).total_seconds()

        creds = gspread.service_account(filename=SERVICE_ACCOUNT_FILE_PATH, scopes=SCOPES)
        spreadsheet = creds.open_by_key(SPREADSHEET_ID)
        worksheet = get_worksheet(spreadsheet, SHEET_NAME_WAIT_TIME)
        
        # スプレッドシートに書き込み
        worksheet.append_row([
            terminal_id,
            start_time_str,
            end_time_str,
            end_status,
            wait_duration_seconds
        ])
        
        print(f"待ち時間記録成功: ターミナルID {terminal_id}, 待ち時間 {wait_duration_seconds}秒")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"エラーが発生しました (log-wait-time):\n{error_details}")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
