// A helper function to get the stored token
async function getToken() {
    // In a real app, you might get this from chrome.storage.local
    // For now, we request it from the popup's in-memory variable, which isn't ideal but works.
    // A better way is to have the popup send the token to the background script when it gets it.
    // Let's implement that.
    
    // First, let's just make it work by having the background ask the app for a token
    // This is less efficient but will work. A better solution is for the popup to "push" the token to us.
    try {
        const response = await fetch('http://127.0.0.1:5000/api/request-token', { method: 'POST' });
        if (!response.ok) return null;
        const data = await response.json();
        return data.token;
    } catch (e) {
        return null;
    }
}

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'GET_PASSWORDS') {
        console.log("Background script received GET_PASSWORDS request.");

        // We define an async function to handle the API call
        const fetchPasswords = async () => {
            const token = await getToken();
            if (!token) {
                console.error("Vault is locked or unreachable. Cannot fetch passwords.");
                sendResponse({ error: "Vault is locked." });
                return;
            }

            try {
                const response = await fetch('http://127.0.0.1:5000/api/get-all-passwords', {
                    method: 'POST', // Match the method in Flask
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                if (!response.ok) throw new Error("Failed to fetch passwords from app.");

                const passwords = await response.json();
                console.log("Successfully fetched passwords:", passwords);
                sendResponse({ passwords: passwords });

            } catch (error) {
                console.error("Error fetching passwords:", error);
                sendResponse({ error: error.message });
            }
        };

        fetchPasswords(); // Execute the async function
        return true; // IMPORTANT: This tells Chrome to keep the message channel open for our async response
    }
});