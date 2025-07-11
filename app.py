from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
import traceback

# Flaskアプリの初期化
app = Flask(__name__)
# CORS設定: 外部ドメインからのアクセスを許可する
CORS(app)

# --- Google Sheetsの設定 ---
# ローカルテスト用に、同じフォルダにあるファイルを読み込む
# SERVICE_ACCOUNT_FILE_PATH = 'C:\python\render-sheet-writeralien-isotope-455823-n4-6db6b2ed6b17.json'
# RenderのSecret Fileから認証情報を読み込む
SERVICE_ACCOUNT_FILE_PATH = '/etc/secrets/alien-isotope-455823-n4-6db6b2ed6b17.json'

SPREADSHEET_ID = '1wP2JQNj2iWTxq68XBzkg_Mb7uZtCC9_6f73G89Ds4Qw'
SHEET_NAME = 'チェック待ちcsv' # 書き込みたいシート名
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

# --- APIのエンドポイントを作成 ---
@app.route('/write', methods=['POST'])
def write_to_sheet():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    timestamp = data.get('timestamp')
    employee_count = data.get('employeeCount')

    if not timestamp or employee_count is None:
        return jsonify({"error": "Missing timestamp or employeeCount"}), 400

    try:
        creds = gspread.service_account(filename=SERVICE_ACCOUNT_FILE_PATH, scopes=SCOPES)
        worksheet = creds.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        worksheet.append_row([timestamp, employee_count])

        print(f"書き込み成功: {timestamp}, {employee_count}")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        # ▼▼▼ エラー発生時に、詳細な情報をログに出力するように変更 ▼▼▼
        error_details = traceback.format_exc()
        print(f"エラーが発生しました:\n{error_details}")
        return jsonify({"error": "Internal Server Error", "details": error_details}), 500

# ローカルでテスト実行するための設定
if __name__ == '__main__':
    app.run(debug=True, port=5000)
