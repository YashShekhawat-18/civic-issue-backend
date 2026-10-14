export default function Spinner({ label = "Loading..." }) {
  return (
    <div role="status" className="flex items-center justify-center gap-3 p-10 text-slate-600">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-blue-600" />
      <span>{label}</span>
    </div>
  );
}
