document.addEventListener('DOMContentLoaded', () => {
    // --- Theme Toggler ---
    const themeToggle = document.getElementById('theme-toggle');
    // ... (keep the existing theme toggler code exactly as it was) ...
    const currentTheme = localStorage.getItem('theme') || 'light';
    
    document.body.classList.add(currentTheme + '-theme');
    themeToggle.innerHTML = currentTheme === 'light' ? '<i class="fas fa-moon"></i>' : '<i class="fas fa-sun"></i>';
    
    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-theme');
        document.body.classList.toggle('light-theme');
        
        let theme = 'light';
        if (document.body.classList.contains('dark-theme')) {
            theme = 'dark';
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
        } else {
            themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
        }
        localStorage.setItem('theme', theme);
    });

    // --- Add Page Functionality ---
    if (document.getElementById('password-form')) {
        const generateBtn = document.getElementById('generate-btn');
        const passwordInput = document.getElementById('password');
        const lengthSlider = document.getElementById('length');
        const lengthValue = document.getElementById('length-value');
        const passwordForm = document.getElementById('password-form');
        const saveBtn = document.getElementById('save-btn'); // Get the save button

        // ... (keep the existing slider and generate button code exactly as it was) ...
        lengthSlider.addEventListener('input', () => {
            lengthValue.textContent = lengthSlider.value;
        });
        
        generateBtn.addEventListener('click', async () => {
            const formData = new FormData();
            formData.append('length', lengthSlider.value);

            const response = await fetch('/generate', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            passwordInput.value = data.password;
        });
        
        generateBtn.click();
        
        // --- NEW: Advanced Animation on Form Submit ---
        passwordForm.addEventListener('submit', (e) => {
            e.preventDefault(); // ALWAYS prevent the default submission first

            // Validate fields before starting animation
            if (!document.getElementById('name').value || !passwordInput.value) {
                alert("Please provide a name for your password.");
                return;
            }
            
            // 1. Start Loading State
            saveBtn.disabled = true;
            saveBtn.classList.add('saving');
            saveBtn.innerHTML = `<span><i class="fas fa-spinner fa-spin"></i> Saving Your Passcode...</span>`;

            // 2. Transition to Success State after a delay
            setTimeout(() => {
                saveBtn.classList.remove('saving');
                saveBtn.classList.add('success');
                saveBtn.innerHTML = `<span><i class="fas fa-check"></i> Success!</span>`;
                
                // 3. Trigger Confetti
                confetti({
                    particleCount: 150,
                    spread: 180,
                    origin: { y: 0.6 }
                });

                // 4. Redirect after showing success
                setTimeout(() => {
                    passwordForm.submit(); // Now, actually submit the form
                }, 1200); // Wait 1.2 seconds to show the success message

            }, 1500); // Wait 1.5 seconds for the "saving" animation
        });
    }
});

// --- Index Page Functionality ---
// ... (keep the copyToClipboard function exactly as it was) ...
function copyToClipboard(button) {
    const input = button.previousElementSibling.previousElementSibling;
    input.select();
    document.execCommand('copy');
    
    const originalIcon = button.innerHTML;
    button.innerHTML = '<i class="fas fa-check"></i>';
    setTimeout(() => {
        button.innerHTML = originalIcon;
    }, 1500);
}

function togglePasswordVisibility(button) {
    // Find the input field within the same parent container
    const input = button.parentElement.querySelector('input');
    // Find the icon element within the button
    const icon = button.querySelector('i');

    // Check the current type of the input field
    if (input.type === "password") {
        // If it's a password, change to text
        input.type = "text";
        // Change the icon to the "eye-slash"
        icon.classList.remove("fa-eye");
        icon.classList.add("fa-eye-slash");
    } else {
        // If it's text, change back to password
        input.type = "password";
        // Change the icon back to the regular "eye"
        icon.classList.remove("fa-eye-slash");
        icon.classList.add("fa-eye");
    }
}