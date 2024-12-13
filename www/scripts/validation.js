// Disable form submission if there are invalid fields
(() => {
    'use strict';

    const forms = document.querySelectorAll('.needs-validation');

    forms.forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }

            form.classList.add('was-validated');
        });
    });
})();

const nameInput = document.getElementById('name');
const macInput = document.getElementById('mac');

const tooltip = new bootstrap.Tooltip(macInput, {
    title: 'MAC address autofilled',
    trigger: 'manual'
});

[nameInput, macInput].forEach(input => {
    input.addEventListener('focus', autofillMac);
});

async function autofillMac() {
    // Prevent autofill if the MAC input already has a value
    if (macInput.value) return;

    try {
        const response = await fetch('/device');

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const { device } = await response.json();
        macInput.value = device || ''; // Autofill or leave empty

        if (device) {
            tooltip.show();

            setTimeout(() => tooltip.hide(), 3000); // Hide tooltip after 3 seconds
        }
    } catch (error) {
        console.error('Error fetching MAC address:', error);
    }
}
