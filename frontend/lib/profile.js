// Checks for the profile page. They mirror the backend rules; the backend still validates again.
const PHONE_RE = /^\+?[0-9]{10,15}$/;

export function validateProfile({ name, phone }) {
  const errors = {};
  const n = name.trim();
  if (n.length < 2) errors.name = "Name must be at least 2 characters";
  else if (n.length > 100) errors.name = "Name must be at most 100 characters";
  if (phone.trim() && !PHONE_RE.test(phone.trim()))
    errors.phone = "Phone must be 10-15 digits, optionally starting with +";
  return errors;
}

// Only send what changed. An emptied phone box is sent as null, which removes the number.
export function profileChanges({ name, phone }, user) {
  const changes = {};
  if (name.trim() !== (user?.name || "")) changes.name = name.trim();
  const newPhone = phone.trim();
  if (newPhone !== (user?.phone || "")) changes.phone = newPhone || null;
  return changes;
}

export function validatePasswordChange({ currentPassword, newPassword, confirmPassword }) {
  const errors = {};
  if (!currentPassword) errors.currentPassword = "Enter your current password";
  if (newPassword.length < 8) errors.newPassword = "Password must be at least 8 characters";
  else if (newPassword.length > 72) errors.newPassword = "Password must be at most 72 characters";
  else if (!/[A-Za-z]/.test(newPassword) || !/\d/.test(newPassword))
    errors.newPassword = "Password must contain at least one letter and one number";
  else if (newPassword === currentPassword) errors.newPassword = "The new password must be different from the current one";
  if (confirmPassword !== newPassword) errors.confirmPassword = "Passwords do not match";
  return errors;
}
