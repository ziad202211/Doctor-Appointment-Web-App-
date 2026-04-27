// Form validation
document.addEventListener('DOMContentLoaded', () => {

// Required field validation
document.querySelectorAll('form').forEach(form => {
form.addEventListener('submit', e => {
    let valid = true;

    form.querySelectorAll('[required]').forEach(field => {
    const group = field.closest('.form-group');
    const errEl = group?.querySelector('.err-msg');

    if (!field.value.trim()) {
        valid = false;
        field.classList.add('error');
        if (errEl) errEl.textContent = 'This field is required.';
    } else {
        field.classList.remove('error');
        if (errEl) errEl.textContent = '';
    }
    });

    // Email validation
    const emailField = form.querySelector('input[type="email"]');
    if (emailField && emailField.value.trim()) {
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const group = emailField.closest('.form-group');
    const errEl = group?.querySelector('.err-msg');
    if (!emailPattern.test(emailField.value)) {
        valid = false;
        emailField.classList.add('error');
        if (errEl) errEl.textContent = 'Enter a valid email address.';
    }
    }

    // Password length
    const pwField = form.querySelector('input[name="password"]');
    if (pwField && pwField.value.trim() && pwField.value.length < 6) {
    valid = false;
    const group = pwField.closest('.form-group');
    const errEl = group?.querySelector('.err-msg');
    pwField.classList.add('error');
    if (errEl) errEl.textContent = 'Password must be at least 6 characters.';
    }

    if (!valid) e.preventDefault();
});
});

// Clear error on input
document.querySelectorAll('input, select').forEach(field => {
field.addEventListener('input', () => {
    field.classList.remove('error');
    const errEl = field.closest('.form-group')?.querySelector('.err-msg');
    if (errEl) errEl.textContent = '';
});
});

// Modal open/close
document.querySelectorAll('[data-modal]').forEach(btn => {
btn.addEventListener('click', () => {
    const id = btn.getAttribute('data-modal');
    document.getElementById(id)?.classList.add('open');
});
});

document.querySelectorAll('[data-close-modal]').forEach(btn => {
btn.addEventListener('click', () => {
    btn.closest('.modal-overlay')?.classList.remove('open');
});
});

document.querySelectorAll('.modal-overlay').forEach(overlay => {
overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.classList.remove('open');
});
});

// Auto-dismiss alerts
document.querySelectorAll('.alert').forEach(alert => {
setTimeout(() => {
    alert.style.transition = 'opacity 0.5s';
    alert.style.opacity = '0';
    setTimeout(() => alert.remove(), 500);
}, 4000);
});

// Disable past dates in date inputs
document.querySelectorAll('input[type="date"]').forEach(input => {
const today = new Date().toISOString().split('T')[0];
input.setAttribute('min', today);
});

});