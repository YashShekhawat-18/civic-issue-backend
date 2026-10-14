const STYLES = {
  error: "border-red-200 bg-red-50 text-red-800",
  success: "border-green-200 bg-green-50 text-green-800",
  info: "border-blue-200 bg-blue-50 text-blue-800",
};

export default function Alert({ type = "info", children }) {
  if (!children) return null;
  return (
    <div role={type === "error" ? "alert" : "status"} className={`rounded-md border px-4 py-3 text-sm ${STYLES[type]}`}>
      {children}
    </div>
  );
}
