from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
import os

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
    # リクエストがJSON形式かチェック
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    timestamp = data.get('timestamp')
    employee_count = data.get('employeeCount')

    # 必要なデータが揃っているかチェック
    if not timestamp or employee_count is None:
        return jsonify({"error": "Missing timestamp or employeeCount"}), 400

    try:
        # 認証情報を読み込んでGoogle Sheetsに接続
        creds = gspread.service_account(filename=SERVICE_ACCOUNT_FILE_PATH, scopes=SCOPES)
        worksheet = creds.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        
        # シートの最終行にデータを追記
        worksheet.append_row([timestamp, employee_count])
        
        print(f"書き込み成功: {timestamp}, {employee_count}")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return jsonify({"error": str(e)}), 500

# ローカルでテスト実行するための設定
if __name__ == '__main__':
    app.run(debug=True, port=5000)
