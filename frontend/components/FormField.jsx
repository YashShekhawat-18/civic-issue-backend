export default function FormField({ id, label, error, hint, ...inputProps }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-slate-700">
        {label}
      </label>
      <input
        id={id}
        name={id}
        aria-invalid={error ? "true" : "false"}
        aria-describedby={error ? `${id}-error` : undefined}
        className={`w-full rounded-md border px-3 py-2 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500 ${
          error ? "border-red-400" : "border-slate-300"
        }`}
        {...inputProps}
      />
      {hint && !error && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
      {error && (
        <p id={`${id}-error`} className="mt-1 text-xs text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}
