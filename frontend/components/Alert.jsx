const STYLES = {
  error: "border-flag/30 bg-flag-tint text-flag",
  success: "border-highway/30 bg-highway-tint text-highway-deep",
  info: "border-sign/30 bg-sign-tint text-sign",
};

export default function Alert({ type = "info", children }) {
  if (!children) return null;
  return (
    <div role={type === "error" ? "alert" : "status"} className={`rounded-lg border px-4 py-3 text-sm font-medium ${STYLES[type]}`}>
      {children}
    </div>
  );
}
