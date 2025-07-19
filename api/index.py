import os
import requests
import json
from flask import Flask, request

app = Flask(__name__)

# --- Environment Variables ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')
JSONBIN_API_KEY = os.environ.get('JSONBIN_API_KEY')
JSONBIN_BIN_ID = os.environ.get('JSONBIN_BIN_ID')

# --- Database Functions ---
def get_db():
    if not JSONBIN_BIN_ID or not JSONBIN_API_KEY: return {'users': []}
    headers = {'X-Master-Key': JSONBIN_API_KEY, 'X-Bin-Meta': 'false'}
    try:
        res = requests.get(f'https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}', headers=headers, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"Error reading from DB: {e}")
        return {'users': []}

def update_db(data):
    if not JSONBIN_BIN_ID or not JSONBIN_API_KEY: return
    headers = {'Content-Type': 'application/json', 'X-Master-Key': JSONBIN_API_KEY}
    try:
        res = requests.put(f'https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}', json=data, headers=headers, timeout=10)
        res.raise_for_status()
    except Exception as e:
        print(f"Error writing to DB: {e}")

# --- Telegram Functions ---
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    requests.post(url, json=payload)

# --- Webhook Handler ---
@app.route('/', methods=['POST'])
def webhook():
    update = request.get_json()
    if 'message' in update:
        message = update['message']
        user_id = message['from']['id']
        chat_id = message['chat']['id']
        text = message.get('text', '')
        
        # 1. Add user to DB
        try:
            db_data = get_db()
            users = db_data.get('users', [])
            if user_id not in users:
                users.append(user_id)
                db_data['users'] = users
                update_db(db_data)
        except Exception as e:
            print(f"Failed to add user {user_id}: {e}")

        # 2. Handle commands
        is_admin = str(user_id) == ADMIN_ID
        
        if text == '/start':
            send_message(chat_id, "Hello! I am a test bot. Send /status to see user count.")
        
        elif is_admin and text == '/status':
            db_data = get_db()
            user_count = len(db_data.get('users', []))
            send_message(chat_id, f"📊 Total Users: *{user_count}*")

        elif is_admin and text.startswith('/broadcast'):
            parts = text.split(' ', 1)
            if len(parts) < 2:
                send_message(chat_id, "Usage: `/broadcast <message>`")
                return 'ok'
            
            message_to_send = parts[1]
            db_data = get_db()
            users = db_data.get('users', [])
            sent_count = 0
            for uid in users:
                try:
                    send_message(uid, message_to_send)
                    sent_count += 1
                except Exception:
                    pass
            send_message(chat_id, f"✅ Broadcast sent to *{sent_count}* of *{len(users)}* users.")

    return 'ok'

@app.route('/')
def index():
    return "Test Bot is running!"
