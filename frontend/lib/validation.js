// Client-side checks mirror the backend rules so users get instant feedback.
// The backend still validates everything again — never trust the browser.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^\+?[0-9]{10,15}$/;

export function validateLogin({ email, password }) {
  const errors = {};
  if (!EMAIL_RE.test(email.trim())) errors.email = "Enter a valid email address";
  if (!password) errors.password = "Enter your password";
  return errors;
}

export function validateRegister({ name, email, password, confirmPassword, phone }) {
  const errors = {};
  if (name.trim().length < 2) errors.name = "Name must be at least 2 characters";
  if (name.trim().length > 100) errors.name = "Name must be at most 100 characters";
  if (!EMAIL_RE.test(email.trim())) errors.email = "Enter a valid email address";
  if (password.length < 8) errors.password = "Password must be at least 8 characters";
  else if (password.length > 72) errors.password = "Password must be at most 72 characters";
  else if (!/[A-Za-z]/.test(password) || !/\d/.test(password))
    errors.password = "Password must contain at least one letter and one number";
  if (confirmPassword !== password) errors.confirmPassword = "Passwords do not match";
  if (phone.trim() && !PHONE_RE.test(phone.trim()))
    errors.phone = "Phone must be 10-15 digits, optionally starting with +";
  return errors;
}

// Turn backend [{field, message}] into {field: message} for the form.
export function fieldErrorsFromApi(errors = []) {
  const out = {};
  for (const e of errors) if (e.field && !out[e.field]) out[e.field] = e.message;
  return out;
}
