// --- Wait for the popup's HTML to be fully loaded ---
document.addEventListener('DOMContentLoaded', () => {

    // --- Get references to all our HTML elements ---
    const passwordDisplay = document.getElementById('passwordDisplay');
    const lengthSlider = document.getElementById('lengthSlider');
    const lengthValue = document.getElementById('lengthValue');
    const generateBtn = document.getElementById('generateBtn');
    const copyBtn = document.getElementById('copyBtn');
    const serviceNameInput = document.getElementById('serviceName');
    const saveBtn = document.getElementById('saveBtn');
    const checkStatusBtn = document.getElementById('checkStatusBtn');
    const statusDiv = document.getElementById('status');

    // This variable will hold our secure token for communicating with the app
    let apiToken = null;

    // --- Password Generation Logic (ported from Python) ---
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
        // Fisher-Yates shuffle for true randomness
        for (let i = passwordArray.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [passwordArray[i], passwordArray[j]] = [passwordArray[j], passwordArray[i]];
        }
        return passwordArray.join('');
    }

    // --- UI Helper Function ---
    function updatePassword() {
        const length = parseInt(lengthSlider.value, 10);
        lengthValue.textContent = length;
        passwordDisplay.value = generatePassword(length);
    }

    // --- API Communication Functions ---

    async function fetchAndStoreToken() {
        try {
            const response = await fetch('http://127.0.0.1:5000/api/request-token', { method: 'POST' });
            if (!response.ok) {
                apiToken = null;
                return;
            }
            const data = await response.json();
            if (data.token) {
                apiToken = data.token;
            }
        } catch (error) {
            console.error("Could not fetch token:", error);
            apiToken = null;
        }
    }

    async function checkAppStatus() {
        statusDiv.textContent = 'Checking...';
        if (!apiToken) {
            await fetchAndStoreToken();
        }
        try {
            const response = await fetch('http://127.0.0.1:5000/api/status', {
                headers: { 'Authorization': `Bearer ${apiToken}` }
            });
            if (!response.ok) throw new Error(`HTTP error!`);
            const data = await response.json();
            statusDiv.textContent = `Vault: ${data.status}`;

            if (data.status === 'unlocked') {
                saveBtn.disabled = false; // Enable the save button if unlocked
            } else {
                apiToken = null;
                saveBtn.disabled = true; // Disable if locked
            }
        } catch (error) {
            statusDiv.textContent = 'App unreachable';
            saveBtn.disabled = true; // Also disable on error
        }
    }

    async function savePassword() {
        const name = serviceNameInput.value;
        const password = passwordDisplay.value;

        if (!name) {
            alert("Please enter a name for the password.");
            return;
        }
        if (!apiToken) {
            alert("Cannot save. The vault is locked or unreachable.");
            return;
        }

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
                    serviceNameInput.value = ''; // Clear input on success
                    updatePassword(); // Generate a new password for the next use
                }, 2000);
            }
        } catch (error) {
            console.error("Save error:", error);
            alert("An error occurred while saving the password.");
            saveBtn.innerHTML = '<i class="fas fa-save"></i> Save to Vault';
            saveBtn.disabled = false; // Re-enable button on error
        }
    }

    // --- Event Listeners ---
    lengthSlider.addEventListener('input', updatePassword);
    generateBtn.addEventListener('click', updatePassword);
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(passwordDisplay.value).then(() => {
            copyBtn.innerHTML = '<i class="fas fa-check"></i>';
            setTimeout(() => {
                copyBtn.innerHTML = '<i class="far fa-copy"></i>';
            }, 1500);
        });
    });
    checkStatusBtn.addEventListener('click', checkAppStatus);
    saveBtn.addEventListener('click', savePassword);

    // --- Initial Run ---
    // When the popup opens, generate a password and check the vault status immediately.
    updatePassword();
    checkAppStatus();
});