// Helpers for the admin "Manage" pages: form checks that mirror the backend rules, and plain-language audit entries.

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^\+?[0-9]{10,15}$/;

// "Street Lighting" -> "STREET_LIGHTING" (the backend wants capital letters, digits and underscores only).
export function suggestCode(name) {
  return name
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 30);
}

export function validateCatalog({ name, code, description, departmentId }, { needsDepartment = false } = {}) {
  const errors = {};
  const n = name.trim();
  if (n.length < 2) errors.name = "Name must be at least 2 characters";
  else if (n.length > 60) errors.name = "Name must be at most 60 characters";
  if (!/^[A-Z0-9_]{2,30}$/.test(code.trim().toUpperCase()))
    errors.code = "Code must be 2-30 characters: letters, digits and underscores only";
  if (description.trim().length > 300) errors.description = "Description must be at most 300 characters";
  if (needsDepartment && !departmentId) errors.departmentId = "Choose a department";
  return errors;
}

export function validateWorker({ name, email, password, phone, departmentId }, { creating }) {
  const errors = {};
  const n = name.trim();
  if (n.length < 2) errors.name = "Name must be at least 2 characters";
  else if (n.length > 100) errors.name = "Name must be at most 100 characters";
  if (creating && !EMAIL_RE.test(email.trim())) errors.email = "Enter a valid email address";
  if (phone.trim() && !PHONE_RE.test(phone.trim())) errors.phone = "Phone must be 10-15 digits, optionally starting with +";
  if (!departmentId) errors.departmentId = "Choose a department";
  if (creating || password) {
    if (password.length < 8) errors.password = "Password must be at least 8 characters";
    else if (password.length > 72) errors.password = "Password must be at most 72 characters";
    else if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) errors.password = "Password must contain at least one letter and one number";
  }
  return errors;
}

// Only send what the admin actually changed (the backend refuses an empty PATCH).
export function changedFields(before, after) {
  const out = {};
  for (const [key, value] of Object.entries(after)) if (before[key] !== value) out[key] = value;
  return out;
}

export const AUDIT_ACTIONS = [
  ["STATUS_CHANGED", "Status changed"],
  ["COMPLAINT_UPDATED", "Complaint edited"],
  ["COMPLAINT_DELETED", "Complaint deleted"],
  ["DEPARTMENT_CREATED", "Department added"],
  ["DEPARTMENT_UPDATED", "Department edited"],
  ["DEPARTMENT_DEACTIVATED", "Department deactivated"],
  ["CATEGORY_CREATED", "Category added"],
  ["CATEGORY_UPDATED", "Category edited"],
  ["CATEGORY_DEACTIVATED", "Category deactivated"],
  ["WORKER_CREATED", "Worker added"],
  ["WORKER_UPDATED", "Worker edited"],
  ["WORKER_DEACTIVATED", "Worker deactivated"],
  ["PASSWORD_CHANGED", "Password changed"],
  ["PROFILE_UPDATED", "Profile updated"],
];
export const AUDIT_ENTITIES = [
  ["COMPLAINT", "Complaints"],
  ["DEPARTMENT", "Departments"],
  ["CATEGORY", "Categories"],
  ["USER", "People"],
];
const ACTION_LABEL = Object.fromEntries(AUDIT_ACTIONS);
const STATUS_WORDS = { SUBMITTED: "Reported", IN_PROGRESS: "Being fixed", RESOLVED: "Resolved" };
const FIELD_WORDS = {
  title: "title", description: "description", priority: "priority", categoryId: "category", departmentId: "department",
  assignedWorker: "assigned worker", name: "name", code: "code", isActive: "active status", phone: "phone",
};
const fieldList = (keys) => (keys.length ? keys.map((k) => FIELD_WORDS[k] || k).join(", ") : "");

/** One audit entry -> { title, detail } in plain words. */
export function describeAudit(entry) {
  const m = entry.metadata || {};
  const label = ACTION_LABEL[entry.action] || entry.action;
  switch (entry.action) {
    case "STATUS_CHANGED":
      return { title: `${m.complaintNumber || "A complaint"}: ${STATUS_WORDS[m.from] || m.from} to ${STATUS_WORDS[m.to] || m.to}`, detail: m.byRole ? `Changed by a ${m.byRole.toLowerCase()}` : "" };
    case "COMPLAINT_UPDATED":
      return { title: `${m.complaintNumber || "A complaint"} edited`, detail: `Changed: ${fieldList(Object.keys(m.changes || {}))}` };
    case "COMPLAINT_DELETED":
      return { title: `${m.complaintNumber || "A complaint"} deleted`, detail: m.title || "" };
    case "DEPARTMENT_CREATED":
    case "CATEGORY_CREATED":
      return { title: `${label}: ${m.name || m.code}`, detail: m.departmentCode ? `In department ${m.departmentCode}` : `Code ${m.code}` };
    case "DEPARTMENT_UPDATED":
    case "CATEGORY_UPDATED":
    case "DEPARTMENT_DEACTIVATED":
    case "CATEGORY_DEACTIVATED":
      return { title: `${label}: ${m.code}`, detail: Object.keys(m.changes || {}).length ? `Changed: ${fieldList(Object.keys(m.changes))}` : "" };
    case "WORKER_CREATED":
      return { title: `${label}: ${m.name}`, detail: m.departmentCode ? `Department ${m.departmentCode}` : "" };
    case "WORKER_UPDATED":
    case "WORKER_DEACTIVATED":
      return { title: label, detail: [m.fields?.length ? `Changed: ${fieldList(m.fields)}` : "", m.passwordReset ? "Password was reset" : ""].filter(Boolean).join(". ") };
    case "PROFILE_UPDATED":
      return { title: label, detail: m.fields?.length ? `Changed: ${fieldList(m.fields)}` : "" };
    default:
      return { title: label, detail: "" };
  }
}
