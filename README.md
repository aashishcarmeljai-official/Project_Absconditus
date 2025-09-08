# Absconditus

A secure, local-first password manager with deep browser integration, built with Python. Absconditus keeps your passwords encrypted on your own machine, accessible via a desktop vault and a seamless browser extension.

---

## Features

*   **Secure, Local Storage:** Your password vault is stored as an encrypted file on your local machine, not in the cloud.
*   **Strong Encryption:** Utilizes AES-256 encryption via the `cryptography` library to protect your data.
*   **Persistent Auto-Unlock:** Integrates with the Windows Data Protection API (DPAPI) to securely store your encryption key, allowing the vault to unlock automatically and safely when you log into your computer.
*   **Browser Extension:** A companion Chrome extension for generating, saving, and autofilling passwords directly in your browser.
*   **Background Service:** Runs as a silent background process with a system tray icon, ensuring the extension can always communicate with the vault.
*   **Modern UI:** A clean, themeable user interface for the desktop vault, built with Flask and PyWebView.

## Installation (for End-Users)

To install Absconditus on your Windows machine, follow these steps:

1.  Go to the **[Releases](https://github.com/aashishcarmeljai-official/Project_Absconditus.git)** section of this repository.
2.  Download the latest installer, `Absconditus-Setup-vX.X.exe`.
3.  Run the installer and follow the on-screen instructions. The setup process will automatically add the background service to your Windows startup.

### First-Time Setup

The first time you run Absconditus, your vault is locked. You must set your master password:
1.  After installation, find the **Absconditus icon** in your system tray (by the clock).
2.  **Right-click** the icon and select **"Unlock Vault"**.
3.  A window will appear. Enter a strong master password. **This password will be used to encrypt your entire vault. Do not forget it!**
4.  Once unlocked, the vault will remain unlocked and will auto-unlock the next time you log into your computer.

## How to Use

### System Tray Icon
The tray icon is the main control center for the background service. Right-clicking it gives you options to:
*   **Unlock Vault:** Manually unlock the vault if it is locked.
*   **Lock Vault:** Manually lock the vault and require a password on the next unlock. This also prevents auto-unlock on the next startup.
*   **Open Vault Window:** Opens the main desktop application where you can view all your saved passwords.
*   **Quit:** Shuts down the background service completely.

### Browser Extension
*   **Generate Passwords:** Click the Absconditus icon in your browser toolbar to open a popup where you can generate secure passwords.
*   **Save Passwords:** While the vault is unlocked, you can name a newly generated password and save it directly to your desktop vault from the extension.
*   **Autofill Passwords:** (Coming soon) The extension will detect password fields and allow you to autofill your saved credentials.

---

## For Developers: Building from Source

This section explains how to build the application and installer from the source code.

### Prerequisites

*   **Python 3.9+**
*   **Git**
*   **Inno Setup Compiler 6:** Download from [jrsoftware.org](https://jrsoftware.org/isinfo.php).

### Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/your-repo.git
    cd PROJECT_ABSCONDITUS
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # For Windows
    python -m venv .venv
    .\.venv\Scripts\activate
    ```

3.  **Install Python dependencies:**
    The project is split into two parts. The dependencies are located in the `desktop_app` directory.
    ```bash
    pip install -r desktop_app/requirements.txt
    ```
    *(If `requirements.txt` does not exist, you can create it with `pip freeze > desktop_app/requirements.txt` after installing the packages manually: `pip install Flask Flask-Cors pystray Pillow pywebview pywin32 cryptography`)*

### Running for Development

You can run the background service directly to test its functionality:
```bash
python desktop_app/background_service.py
```

### Building the Executables with PyInstaller

The application is packaged into two separate executables. Run these commands from the root `PROJECT_ABSCONDITUS` directory.

1.  **Build the Background Service:**
    ```bash
    pyinstaller --name "Absconditus_Service" --onefile --windowed --add-data "desktop_app/templates;templates" --add-data "desktop_app/static;static" --add-data "desktop_app/icon.ico;." --hidden-import "win32timezone" desktop_app/background_service.py
    ```

2.  **Build the GUI Client:**
    ```bash
    pyinstaller --name "Absconditus_GUI" --onefile --windowed --icon="desktop_app/icon.ico" desktop_app/gui_client.py
    ```

These commands will place `Absconditus_Service.exe` and `Absconditus_GUI.exe` inside the `dist` folder.

### Creating the Installer with Inno Setup

1.  Make sure the executables from the previous step exist in a `dist` folder inside `desktop_app`. The Inno Setup script looks for them at `desktop_app/dist/`.
2.  Open the **Inno Setup Compiler**.
3.  Go to `File > Open...` and select the `desktop_app/setup_script.iss` file.
4.  Click the **Compile** button (or press F9).
5.  The final installer, `Absconditus-Setup-v1.0.exe`, will be created in the `desktop_app/Output` folder.

### Loading the Browser Extension for Development

1.  Open Chrome and navigate to `chrome://extensions`.
2.  Enable **"Developer mode"**.
3.  Click **"Load unpacked"**.
4.  Select the `browser_extension` folder.

## Project Structure

```
PROJECT_ABSCONDITUS/
│
├── browser_extension/  # Source code for the Chrome extension
│
└── desktop_app/        # Source code for the desktop application
    ├── background_service.py # The core API server and tray icon logic
    ├── gui_client.py         # The on-demand vault window
    ├── setup_script.iss      # Inno Setup script for the installer
    ├── static/               # CSS and JS for the web UI
    └── templates/            # HTML templates for the web UI
```