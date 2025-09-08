import json
import string
import random
import os
import base64
import hashlib
import sys
import webview
import secrets  # Used for generating secure tokens
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask_cors import CORS
from multiprocessing import Process, freeze_support
import time

# --- APP INITIALIZATION & CONFIG ---
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for Flask sessions (for the desktop app)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Allows the extension to talk to the API

# --- CONSTANTS AND DATA SETUP ---
APP_NAME = "Absconditus"
APPDATA_FOLDER = os.path.join(os.getenv('LOCALAPPDATA'), APP_NAME)
os.makedirs(APPDATA_FOLDER, exist_ok=True)
DATA_FILE = os.path.join(APPDATA_FOLDER, 'passwords.dat')
SALT_FILE = os.path.join(APPDATA_FOLDER, 'salt.key')
API_PORT = 5000

# --- GLOBAL STATE MANAGEMENT ---
# These variables manage the "unlocked" state for the API
API_ACCESS_TOKEN = None
CURRENT_ENCRYPTION_KEY = None # Stores the key in memory while app is unlocked

# --- ENCRYPTION AND HELPER FUNCTIONS ---
def get_salt():
    if not os.path.exists(SALT_FILE):
        salt = os.urandom(16)
        with open(SALT_FILE, 'wb') as f:
            f.write(salt)
        return salt
    with open(SALT_FILE, 'rb') as f:
        return f.read()

SALT = get_salt()

def derive_key(master_password: str) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=SALT, iterations=480000)
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

def encrypt_data(data: dict, key: bytes) -> bytes:
    return Fernet(key).encrypt(json.dumps(data).encode())

def decrypt_data(encrypted_data: bytes, key: bytes) -> dict:
    return json.loads(Fernet(key).decrypt(encrypted_data))

# --- DATA PERSISTENCE (for session-based GUI) ---
def load_passwords():
    if 'encryption_key' not in session: return None
    key = session['encryption_key'].encode()
    try:
        with open(DATA_FILE, 'rb') as f:
            encrypted_data = f.read()
        return {} if not encrypted_data else decrypt_data(encrypted_data, key)
    except FileNotFoundError:
        return {}
    except InvalidToken:
        return None

def save_passwords(passwords: dict):
    if 'encryption_key' not in session: return
    key = session['encryption_key'].encode()
    with open(DATA_FILE, 'wb') as f:
        f.write(encrypt_data(passwords, key))

def generate_password(length=16):
    if length < 4: length = 4
    chars = string.ascii_letters + string.digits + string.punctuation
    pwd = [random.choice(string.ascii_lowercase), random.choice(string.ascii_uppercase), random.choice(string.digits), random.choice(string.punctuation)]
    pwd += [random.choice(chars) for _ in range(length - 4)]
    random.shuffle(pwd)
    return "".join(pwd)

# --- DESKTOP APP GUI FLASK ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    global API_ACCESS_TOKEN, CURRENT_ENCRYPTION_KEY

    if request.method == 'POST':
        master_password = request.form['password']
        key = derive_key(master_password)
        try:
            with open(DATA_FILE, 'rb') as f: encrypted_data = f.read()
            if encrypted_data: decrypt_data(encrypted_data, key)
            
            # On success, set session for GUI and global vars for API
            session['encryption_key'] = key.decode()
            API_ACCESS_TOKEN = secrets.token_hex(32)
            CURRENT_ENCRYPTION_KEY = key
            return redirect(url_for('index'))
        except FileNotFoundError:
            session['encryption_key'] = key.decode()
            API_ACCESS_TOKEN = secrets.token_hex(32)
            CURRENT_ENCRYPTION_KEY = key
            return redirect(url_for('index'))
        except InvalidToken:
            API_ACCESS_TOKEN = None
            CURRENT_ENCRYPTION_KEY = None
            flash('Incorrect master password.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    global API_ACCESS_TOKEN, CURRENT_ENCRYPTION_KEY
    session.pop('encryption_key', None)
    API_ACCESS_TOKEN = None
    CURRENT_ENCRYPTION_KEY = None
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'encryption_key' not in session: return redirect(url_for('login'))
    passwords = load_passwords()
    if passwords is None: return redirect(url_for('logout'))
    return render_template('index.html', passwords=passwords)

@app.route('/add')
def add():
    if 'encryption_key' not in session: return redirect(url_for('login'))
    return render_template('add.html')

@app.route('/generate', methods=['POST'])
def generate():
    if 'encryption_key' not in session: return jsonify({'error': 'Not authenticated'}), 401
    length = int(request.form.get('length', 16))
    return jsonify({'password': generate_password(length)})

@app.route('/save', methods=['POST'])
def save():
    if 'encryption_key' not in session: return redirect(url_for('login'))
    name, password = request.form['name'], request.form['password']
    if name and password:
        passwords = load_passwords()
        passwords[name] = password
        save_passwords(passwords)
    return redirect(url_for('index'))

@app.route('/delete', methods=['POST'])
def delete():
    if 'encryption_key' not in session: return redirect(url_for('login'))
    name_to_delete = request.form['name']
    passwords = load_passwords()
    if name_to_delete in passwords:
        del passwords[name_to_delete]
        save_passwords(passwords)
    return redirect(url_for('index'))

# --- BROWSER EXTENSION API ROUTES ---

@app.route('/api/status', methods=['GET'])
def api_status():
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith("Bearer ") and auth_header.split(" ")[1] == API_ACCESS_TOKEN:
        return jsonify({'status': 'unlocked'})
    return jsonify({'status': 'locked'})

@app.route('/api/request-token', methods=['POST'])
def request_token():
    if API_ACCESS_TOKEN:
        return jsonify({'token': API_ACCESS_TOKEN})
    else:
        return jsonify({'error': 'Vault is locked'}), 403

@app.route('/api/save-password', methods=['POST'])
def api_save_password():
    # 1. Security Check: Validate the token
    auth_header = request.headers.get('Authorization')
    if not (auth_header and auth_header.startswith("Bearer ") and auth_header.split(" ")[1] == API_ACCESS_TOKEN):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # 2. Check if the vault is unlocked (key exists in memory)
    if not CURRENT_ENCRYPTION_KEY:
        return jsonify({'error': 'Vault is locked'}), 403

    # 3. Get the data from the extension
    data = request.get_json()
    name = data.get('name')
    password = data.get('password')
    if not name or not password:
        return jsonify({'error': 'Missing name or password'}), 400

    # 4. Perform the save operation
    try:
        passwords = {}
        if os.path.exists(DATA_FILE):
             with open(DATA_FILE, 'rb') as f:
                encrypted_data = f.read()
             if encrypted_data:
                passwords = decrypt_data(encrypted_data, CURRENT_ENCRYPTION_KEY)
        
        passwords[name] = password
        new_encrypted_data = encrypt_data(passwords, CURRENT_ENCRYPTION_KEY)
        with open(DATA_FILE, 'wb') as f:
            f.write(new_encrypted_data)

        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error saving password via API: {e}", file=sys.stderr)
        return jsonify({'error': 'Failed to save data'}), 500

# --- LAUNCHER ---
def start_api_server():
    app.run(host='127.0.0.1', port=API_PORT)

if __name__ == '__main__':
    freeze_support()
    api_process = Process(target=start_api_server, daemon=True)
    api_process.start()
    time.sleep(1)
    webview.create_window(
        "Absconditus",
        url=f"http://127.0.0.1:{API_PORT}",
        width=1200,
        height=800,
        resizable=True
    )
    webview.start(debug=False, http_server="waitress")