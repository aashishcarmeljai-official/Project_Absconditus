// --- Wait for the popup's HTML to be fully loaded ---
document.addEventListener('DOMContentLoaded', () => {

    // --- Get references to all UI elements ---
    const unlockedView = document.getElementById('unlockedView');
    const lockedView = document.getElementById('lockedView');
    const passwordDisplay = document.getElementById('passwordDisplay');
    const lengthSlider = document.getElementById('lengthSlider');
    const lengthValue = document.getElementById('lengthValue');
    const generateBtn = document.getElementById('generateBtn');
    const copyBtn = document.getElementById('copyBtn');
    const serviceNameInput = document.getElementById('serviceName');
    const saveBtn = document.getElementById('saveBtn');
    const statusDiv = document.getElementById('status');
    const masterPasswordInput = document.getElementById('masterPassword');
    const unlockBtn = document.getElementById('unlockBtn');
    const unlockError = document.getElementById('unlockError');

    // This variable holds our secure token for communicating with the app
    let apiToken = null;

    // --- UI View Management ---
    function showUnlockedView() {
        lockedView.style.display = 'none';
        unlockedView.style.display = 'block';
        statusDiv.textContent = 'Vault: Unlocked';
        saveBtn.disabled = false;
    }

    function showLockedView() {
        unlockedView.style.display = 'none';
        lockedView.style.display = 'block';
        statusDiv.textContent = 'Vault: Locked';
        unlockError.textContent = ''; // Clear any previous errors
        masterPasswordInput.focus(); // Set focus for immediate typing
    }

    // --- Password Generation Logic ---
    function generatePassword(length) {
        const lower = 'abcdefghijklmnopqrstuvwxyz';
        const upper = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
        const digits = '0123456789';
        const symbols = '!@#$%^&*()_+-=[]{}|;:,.<>/?';
        const allChars = lower + upper + digits + symbols;
        let passwordArray = [
            lower[Math.floor(Math.random() * lower.length)],
            upper[Math.floor(Math.random() * upper.length)],
            digits[Math.floor(Math.random() * digits.length)],
            symbols[Math.floor(Math.random() * symbols.length)]
        ];
        for (let i = 4; i < length; i++) {
            passwordArray.push(allChars[Math.floor(Math.random() * allChars.length)]);
        }
        for (let i = passwordArray.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [passwordArray[i], passwordArray[j]] = [passwordArray[j], passwordArray[i]];
        }
        return passwordArray.join('');
    }

    function updatePassword() {
        const length = parseInt(lengthSlider.value, 10);
        lengthValue.textContent = length;
        passwordDisplay.value = generatePassword(length);
    }

    // --- API Communication Functions ---
    async function checkAppStatus() {
        statusDiv.textContent = 'Checking...';
        try {
            // We first try to get a token. If this works, the app is already unlocked.
            const tokenResponse = await fetch('http://127.0.0.1:5000/api/request-token', { method: 'POST' });
            if (tokenResponse.ok) {
                const tokenData = await tokenResponse.json();
                apiToken = tokenData.token;
                showUnlockedView();
            } else {
                // If we can't get a token, the vault is locked.
                apiToken = null;
                showLockedView();
            }
        } catch (error) {
            // If we can't even reach the server, show the locked view and an error.
            statusDiv.textContent = 'App unreachable';
            showLockedView();
        }
    }

    async function unlockVault() {
        const password = masterPasswordInput.value;
        if (!password) {
            unlockError.textContent = 'Password cannot be empty.';
            return;
        }
        unlockBtn.innerHTML = 'Unlocking...';
        unlockBtn.disabled = true;
        unlockError.textContent = '';

        try {
            const response = await fetch('http://127.0.0.1:5000/api/unlock', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: password })
            });

            if (response.ok) {
                // If unlock was successful, we re-run the status check.
                // This will now get a valid token and switch the UI to the unlocked view.
                await checkAppStatus();
            } else {
                unlockError.textContent = 'Invalid master password.';
            }
        } catch (error) {
            unlockError.textContent = 'Error communicating with the app.';
        } finally {
            // For security, always clear the password field
            masterPasswordInput.value = '';
            // Re-enable the button
            unlockBtn.innerHTML = '<i class="fas fa-lock-open"></i> Unlock';
            unlockBtn.disabled = false;
        }
    }

    async function savePassword() {
        const name = serviceNameInput.value;
        const password = passwordDisplay.value;
        if (!name) { alert("Please enter a name for the password."); return; }
        if (!apiToken) { alert("Cannot save. The vault is locked or unreachable."); return; }

        saveBtn.innerHTML = 'Saving...';
        saveBtn.disabled = true;

        try {
            const response = await fetch('http://127.0.0.1:5000/api/save-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${apiToken}`
                },
                body: JSON.stringify({ name: name, password: password })
            });
            if (!response.ok) throw new Error('Server rejected the save request.');
            const result = await response.json();
            if (result.status === 'success') {
                saveBtn.innerHTML = 'Saved!';
                setTimeout(() => {
                    saveBtn.innerHTML = '<i class="fas fa-save"></i> Save to Vault';
                    saveBtn.disabled = false;
                    serviceNameInput.value = '';
                    updatePassword();
                }, 2000);
            }
        } catch (error) {
            console.error("Save error:", error);
            alert("An error occurred while saving the password.");
            saveBtn.innerHTML = '<i class="fas fa-save"></i> Save to Vault';
            saveBtn.disabled = false;
        }
    }

    // --- Event Listeners ---
    lengthSlider.addEventListener('input', updatePassword);
    generateBtn.addEventListener('click', updatePassword);
    unlockBtn.addEventListener('click', unlockVault);
    saveBtn.addEventListener('click', savePassword);
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(passwordDisplay.value).then(() => {
            copyBtn.innerHTML = '<i class="fas fa-check"></i>';
            setTimeout(() => {
                copyBtn.innerHTML = '<i class="far fa-copy"></i>';
            }, 1500);
        });
    });

    // --- Initial Run ---
    // Pre-fill the generator and then check the vault status to decide which view to show.
    updatePassword();
    checkAppStatus();
});