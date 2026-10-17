// Roles must match the backend enum exactly.
export const ROLES = { CITIZEN: "CITIZEN", WORKER: "WORKER", ADMIN: "ADMIN" };

// Where each role lands after login.
export const ROLE_HOME = {
  CITIZEN: "/citizen",
  WORKER: "/worker",
  ADMIN: "/admin",
};

export function homeFor(role) {
  return ROLE_HOME[role] || "/login";
}

// Menu links per role (extended in later phases).
export const ROLE_MENU = {
  CITIZEN: [
    { href: "/citizen", label: "Home" },
    { href: "/citizen/report", label: "Report an issue" },
    { href: "/citizen/complaints", label: "My complaints" },
    { href: "/citizen/nearby", label: "Nearby" },
    { href: "/citizen/notifications", label: "Alerts" },
    { href: "/citizen/rewards", label: "Rewards" },
  ],
  WORKER: [
    { href: "/worker", label: "Dashboard" },
    { href: "/worker/tasks", label: "Tasks" },
  ],
  ADMIN: [{ href: "/admin", label: "Dashboard" }],
};
