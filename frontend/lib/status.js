// The backend has exactly three complaint statuses. We show them in plain words.
export const STATUS_ORDER = ["SUBMITTED", "IN_PROGRESS", "RESOLVED"];

export const STATUS_INFO = {
  SUBMITTED: { label: "Reported", plain: "Sent to the department", pill: "bg-sign-tint text-sign" },
  IN_PROGRESS: { label: "Being fixed", plain: "A worker is on it", pill: "bg-signal-tint text-asphalt" },
  RESOLVED: { label: "Resolved", plain: "The issue is fixed", pill: "bg-highway-tint text-highway-deep" },
};

export function statusInfo(status) {
  return STATUS_INFO[status] || { label: status || "Unknown", plain: "", pill: "bg-concrete text-asphalt" };
}

export function statusIndex(status) {
  const i = STATUS_ORDER.indexOf(status);
  return i < 0 ? 0 : i;
}
