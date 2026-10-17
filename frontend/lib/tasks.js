// What each filter asks the backend for.
export const FILTERS = [
  { key: "new", label: "New", query: { status: "SUBMITTED" }, empty: "No new reports" },
  { key: "mine", label: "My jobs", query: { status: "IN_PROGRESS", assignedToMe: "true" }, empty: "You have no jobs in progress" },
  { key: "overdue", label: "Overdue", query: { overdue: "true" }, empty: "Nothing is overdue" },
  { key: "resolved", label: "Resolved", query: { status: "RESOLVED" }, empty: "Nothing has been resolved yet" },
  { key: "all", label: "All", query: {}, empty: "Your department has no complaints yet" },
];

