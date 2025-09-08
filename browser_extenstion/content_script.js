console.log("Absconditus content script injected!");

// --- Main Function to inject icon ---
function injectIcon(passwordField) {
    if (passwordField.parentElement.classList.contains('absconditus-icon-wrapper')) return;
    const wrapper = document.createElement('div');
    wrapper.className = 'absconditus-icon-wrapper';
    passwordField.parentNode.insertBefore(wrapper, passwordField);
    wrapper.appendChild(passwordField);
    const icon = document.createElement('div');
    icon.className = 'absconditus-autofill-icon';
    icon.title = 'Autofill with Absconditus';
    wrapper.appendChild(icon);

    icon.addEventListener('click', (e) => {
        e.stopPropagation();
        // When icon is clicked, ask the background for passwords
        chrome.runtime.sendMessage({ type: 'GET_PASSWORDS' }, (response) => {
            if (response && response.passwords) {
                // If we get passwords, create the autofill menu
                createAutofillMenu(passwordField, response.passwords, wrapper);
            } else {
                console.error("Could not get passwords:", response.error);
                // Optional: Show a small error message
                alert(`Absconditus: ${response.error || 'Could not connect to the app.'}`);
            }
        });
    });
}

// --- NEW: Function to create the autofill dropdown menu ---
function createAutofillMenu(passwordField, passwords, wrapper) {
    // Remove any existing menu first
    const existingMenu = wrapper.querySelector('.absconditus-menu');
    if (existingMenu) existingMenu.remove();

    const menu = document.createElement('div');
    menu.className = 'absconditus-menu';

    const passwordEntries = Object.entries(passwords);

    if (passwordEntries.length === 0) {
        menu.innerHTML = '<div class="absconditus-menu-item">No passwords saved yet.</div>';
    } else {
        passwordEntries.forEach(([name, password]) => {
            const item = document.createElement('div');
            item.className = 'absconditus-menu-item';
            item.textContent = name; // Show the name of the password
            item.addEventListener('click', () => {
                // --- THIS IS THE AUTOFILL ACTION ---
                passwordField.value = password;
                // Optional: Try to find and fill the username too
                const usernameField = findUsernameField(passwordField);
                if (usernameField) {
                    // This is a simple guess, might not always work
                    usernameField.value = name;
                }
                menu.remove(); // Close menu after selection
            });
            menu.appendChild(item);
        });
    }
    wrapper.appendChild(menu);

    // Add a listener to close the menu if the user clicks elsewhere
    setTimeout(() => {
        document.addEventListener('click', () => menu.remove(), { once: true });
    }, 0);
}

// --- NEW: Helper function to find the username field (simple version) ---
function findUsernameField(passwordField) {
    const form = passwordField.closest('form');
    if (!form) return null;
    // Look for an input with type=email, type=text, or name containing 'user' or 'email'
    return form.querySelector('input[type="email"], input[type="text"][name*="user"], input[type="text"][name*="email"]');
}

// --- Run the injection ---
document.querySelectorAll('input[type="password"]').forEach(injectIcon);