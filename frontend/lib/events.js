// Tiny "something changed" signal between components that do not share a parent.
export const NOTIFICATIONS_CHANGED = "civic:notifications-changed";

export function announceNotificationsChanged() {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(NOTIFICATIONS_CHANGED));
}
