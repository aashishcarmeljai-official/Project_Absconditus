# --- IMPORTS ---
# Standard library imports
import os
import sys
import json
import string
import random
import base64
import hashlib
import secrets
import threading
import time
import platform

# Third-party library imports
# Make sure to run: pip install Flask Flask-Cors pystray Pillow pywebview pywin32
from PIL import Image
from pystray import Icon, Menu, MenuItem
from flask import Flask, jsonify, request, render_template, flash, session, redirect, url_for
from flask_cors import CORS
import webview

# Cryptography imports
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Windows-specific import for secure key storage
if platform.system() == "Windows":
    import win32crypt

# --- FLASK APP INITIALIZATION ---
app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app, resources={r"/api/*": {"origins": "*"}})

unlock_app = Flask("unlock_app")
unlock_app.secret_key = os.urandom(24)

# --- CONSTANTS AND GLOBAL STATE ---
APP_NAME = "Absconditus"
APPDATA_FOLDER = os.path.join(os.getenv('LOCALAPPDATA'), APP_NAME)
os.makedirs(APPDATA_FOLDER, exist_ok=True)
DATA_FILE = os.path.join(APPDATA_FOLDER, 'passwords.dat')
SALT_FILE = os.path.join(APPDATA_FOLDER, 'salt.key')
PROTECTED_KEY_FILE = os.path.join(APPDATA_FOLDER, 'key.protected') # For auto-unlock
API_PORT = 5000
UNLOCK_PORT = 5001

API_ACCESS_TOKEN = None
CURRENT_ENCRYPTION_KEY = None
unlock_window = None

# --- DPAPI KEY PROTECTION FUNCTIONS (Windows Only) ---
def protect_key(key: bytes) -> bytes:
    """Encrypts the key using the current user's DPAPI credentials."""
    return win32crypt.CryptProtectData(key, None, None, None, None, 0)

def unprotect_key() -> bytes | None:
    """Decrypts the key using the current user's DPAPI credentials."""
    try:
        with open(PROTECTED_KEY_FILE, 'rb') as f:
            encrypted_key = f.read()
        # DecryptData returns a tuple, the second element is the decrypted data
        return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    except Exception as e:
        print(f"Could not unprotect key: {e}", file=sys.stderr)
        return None

# --- CORE ENCRYPTION & HELPER FUNCTIONS ---
def get_salt():
    if not os.path.exists(SALT_FILE):
        salt = os.urandom(16)
        with open(SALT_FILE, 'wb') as f: f.write(salt)
        return salt
    with open(SALT_FILE, 'rb') as f: return f.read()
SALT = get_salt()

def derive_key(master_password: str) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=SALT, iterations=480000)
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

def encrypt_data(data: dict, key: bytes) -> bytes:
    return Fernet(key).encrypt(json.dumps(data).encode())

def decrypt_data(encrypted_data: bytes, key: bytes) -> dict:
    return json.loads(Fernet(key).decrypt(encrypted_data))

def generate_password(length=16):
    if length < 4: length = 4
    chars = string.ascii_letters + string.digits + string.punctuation
    pwd = [random.choice(string.ascii_lowercase), random.choice(string.ascii_uppercase), random.choice(string.digits), random.choice(string.punctuation)]
    pwd += [random.choice(chars) for _ in range(length - 4)]
    random.shuffle(pwd)
    return "".join(pwd)

# --- DATA FUNCTIONS (Used by the Main GUI's session) ---
def load_passwords():
    if 'encryption_key' not in session: return None
    key = session['encryption_key'].encode()
    try:
        with open(DATA_FILE, 'rb') as f: encrypted_data = f.read()
        return {} if not encrypted_data else decrypt_data(encrypted_data, key)
    except FileNotFoundError: return {}
    except InvalidToken: return None

def save_passwords(passwords: dict):
    if 'encryption_key' not in session: return
    key = session['encryption_key'].encode()
    with open(DATA_FILE, 'wb') as f: f.write(encrypt_data(passwords, key))

# --- MAIN FLASK ROUTES (for API and Main GUI) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    global API_ACCESS_TOKEN, CURRENT_ENCRYPTION_KEY
    if request.method == 'POST':
        master_password = request.form['password']
        key = derive_key(master_password)
        try:
            with open(DATA_FILE, 'rb') as f: encrypted_data = f.read()
            if encrypted_data: decrypt_data(encrypted_data, key)
            
            session['encryption_key'] = key.decode()
            API_ACCESS_TOKEN = secrets.token_hex(32)
            CURRENT_ENCRYPTION_KEY = key
            
            # On successful login, protect and store the key for future auto-unlock
            encrypted_key_for_storage = protect_key(key)
            with open(PROTECTED_KEY_FILE, 'wb') as f:
                f.write(encrypted_key_for_storage)
                
            return redirect(url_for('index'))
        except (FileNotFoundError, InvalidToken):
            flash('Incorrect master password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('encryption_key', None)
    # This route is for the GUI, locking the vault is handled by the tray icon
    return redirect(url_for('login'))

# (All other GUI routes are unchanged)
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
@app.route('/api/get-all-passwords', methods=['POST'])
def api_get_all_passwords():
    # 1. Security Check: Validate the token
    auth_header = request.headers.get('Authorization')
    if not (auth_header and auth_header.startswith("Bearer ") and auth_header.split(" ")[1] == API_ACCESS_TOKEN):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # 2. Check if the vault is unlocked
    if not CURRENT_ENCRYPTION_KEY:
        return jsonify({'error': 'Vault is locked'}), 403

    # 3. Load, decrypt, and return all passwords
    try:
        passwords = {}
        if os.path.exists(DATA_FILE):
             with open(DATA_FILE, 'rb') as f:
                encrypted_data = f.read()
             if encrypted_data:
                passwords = decrypt_data(encrypted_data, CURRENT_ENCRYPTION_KEY)
        
        return jsonify(passwords) # Return the entire decrypted dictionary
    except Exception as e:
        print(f"Error getting all passwords: {e}", file=sys.stderr)
        return jsonify({'error': 'Failed to retrieve data'}), 500
@app.route('/api/unlock', methods=['POST'])
def api_unlock():
    global API_ACCESS_TOKEN, CURRENT_ENCRYPTION_KEY
    
    data = request.get_json()
    master_password = data.get('password')

    if not master_password:
        return jsonify({'error': 'Password is required'}), 400

    key = derive_key(master_password)
    try:
        # Perform the same decryption test as the login page
        with open(DATA_FILE, 'rb') as f:
            encrypted_data = f.read()
        if encrypted_data:
            decrypt_data(encrypted_data, key)
        
        # --- SUCCESS! Unlock the service ---
        API_ACCESS_TOKEN = secrets.token_hex(32)
        CURRENT_ENCRYPTION_KEY = key
        
        # Persist the key for auto-unlock on next restart
        if platform.system() == "Windows":
            encrypted_key_for_storage = protect_key(key)
            with open(PROTECTED_KEY_FILE, 'wb') as f:
                f.write(encrypted_key_for_storage)
        
        return jsonify({'status': 'success'})

    except (FileNotFoundError, InvalidToken):
        # --- FAILURE! ---
        API_ACCESS_TOKEN = None
        CURRENT_ENCRYPTION_KEY = None
        return jsonify({'error': 'Invalid password'}), 401 # 401 Unauthorized
@app.route('/api/status', methods=['GET'])
def api_status():
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith("Bearer ") and auth_header.split(" ")[1] == API_ACCESS_TOKEN:
        return jsonify({'status': 'unlocked'})
    return jsonify({'status': 'locked'})
@app.route('/api/request-token', methods=['POST'])
def request_token():
    if API_ACCESS_TOKEN: return jsonify({'token': API_ACCESS_TOKEN})
    else: return jsonify({'error': 'Vault is locked'}), 403
@app.route('/api/save-password', methods=['POST'])
def api_save_password():
    auth_header = request.headers.get('Authorization')
    if not (auth_header and auth_header.startswith("Bearer ") and auth_header.split(" ")[1] == API_ACCESS_TOKEN):
        return jsonify({'error': 'Unauthorized'}), 401
    if not CURRENT_ENCRYPTION_KEY: return jsonify({'error': 'Vault is locked'}), 403
    data = request.get_json()
    name, password = data.get('name'), data.get('password')
    if not name or not password: return jsonify({'error': 'Missing name or password'}), 400
    try:
        passwords = {}
        if os.path.exists(DATA_FILE):
             with open(DATA_FILE, 'rb') as f: encrypted_data = f.read()
             if encrypted_data: passwords = decrypt_data(encrypted_data, CURRENT_ENCRYPTION_KEY)
        passwords[name] = password
        new_encrypted_data = encrypt_data(passwords, CURRENT_ENCRYPTION_KEY)
        with open(DATA_FILE, 'wb') as f: f.write(new_encrypted_data)
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error saving password via API: {e}", file=sys.stderr)
        return jsonify({'error': 'Failed to save data'}), 500

# --- UNLOCK DIALOG (Served by the temporary 'unlock_app') ---
@unlock_app.route('/', methods=['GET', 'POST'])
def unlock_page():
    global API_ACCESS_TOKEN, CURRENT_ENCRYPTION_KEY, unlock_window
    if request.method == 'POST':
        master_password = request.form['password']
        key = derive_key(master_password)
        try:
            with open(DATA_FILE, 'rb') as f: encrypted_data = f.read()
            if encrypted_data: decrypt_data(encrypted_data, key)
            API_ACCESS_TOKEN = secrets.token_hex(32)
            CURRENT_ENCRYPTION_KEY = key

            # On success, protect and store the key
            encrypted_key_for_storage = protect_key(key)
            with open(PROTECTED_KEY_FILE, 'wb') as f:
                f.write(encrypted_key_for_storage)
            
            if unlock_window: unlock_window.destroy()
            return "<h1>Vault Unlocked!</h1><p>You can close this window now.</p>"
        except (FileNotFoundError, InvalidToken):
            flash('Incorrect master password.', 'error')
    return render_template('login.html')

# --- TRAY ICON & LAUNCHER LOGIC ---
def run_api_server():
    app.run(host='127.0.0.1', port=API_PORT)

def run_unlock_server():
    unlock_app.run(host='127.0.0.1', port=UNLOCK_PORT)

def show_unlock_window(icon, item):
    global unlock_window
    if unlock_window and unlock_window.active: return
    unlock_server_thread = threading.Thread(target=run_unlock_server, daemon=True)
    unlock_server_thread.start()
    time.sleep(1)
    unlock_window = webview.create_window("Unlock Absconditus", f"http://127.0.0.1:{UNLOCK_PORT}", width=500, height=550)

def open_vault_window(icon, item):
    webview.create_window("Absconditus", f"http://127.0.0.1:{API_PORT}", width=1200, height=800, resizable=True)

def lock_vault(icon, item):
    global API_ACCESS_TOKEN, CURRENT_ENCRYPTION_KEY
    API_ACCESS_TOKEN, CURRENT_ENCRYPTION_KEY = None, None
    if os.path.exists(PROTECTED_KEY_FILE):
        os.remove(PROTECTED_KEY_FILE)

def quit_app(icon, item):
    icon.stop()
    os._exit(0)

def setup_tray_icon():
    image = Image.open(resource_path("icon.ico"))
    menu = Menu(
        MenuItem('Unlock Vault', show_unlock_window, enabled=lambda item: CURRENT_ENCRYPTION_KEY is None),
        MenuItem('Lock Vault', lock_vault, enabled=lambda item: CURRENT_ENCRYPTION_KEY is not None),
        MenuItem('Open Vault Window', open_vault_window, default=True),
        Menu.SEPARATOR,
        MenuItem('Quit', quit_app)
    )
    icon = Icon("Absconditus", image, "Absconditus", menu)
    icon.run()

def attempt_auto_unlock():
    """Called when the service first starts to unlock the vault automatically."""
    global CURRENT_ENCRYPTION_KEY, API_ACCESS_TOKEN
    if platform.system() != "Windows":
        print("Auto-unlock feature is only available on Windows.", file=sys.stderr)
        return
    decrypted_key = unprotect_key()
    if decrypted_key:
        print("Successfully decrypted stored key. Vault is unlocked automatically.")
        CURRENT_ENCRYPTION_KEY = decrypted_key
        API_ACCESS_TOKEN = secrets.token_hex(32)
    else:
        print("No stored key found or decryption failed. Vault remains locked.")

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if __name__ == '__main__':
    # Attempt to auto-unlock as the very first step
    attempt_auto_unlock()

    # Start the main API server in a background thread
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    
    # The system tray icon is the main process for the background service
    setup_tray_icon()