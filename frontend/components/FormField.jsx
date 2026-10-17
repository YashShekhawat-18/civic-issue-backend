export default function FormField({ id, label, error, hint, ...inputProps }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-semibold text-asphalt">
        {label}
      </label>
      <input
        id={id}
        name={id}
        aria-invalid={error ? "true" : "false"}
        aria-describedby={error ? `${id}-error` : undefined}
        className={`w-full rounded-lg border bg-white px-3.5 py-2.5 text-asphalt placeholder:text-asphalt-soft/60 ${
          error ? "border-flag" : "border-line hover:border-asphalt-soft/50"
        }`}
        {...inputProps}
      />
      {hint && !error && <p className="mt-1.5 text-xs text-asphalt-soft">{hint}</p>}
      {error && (
        <p id={`${id}-error`} className="mt-1.5 text-xs font-medium text-flag">
          {error}
        </p>
      )}
    </div>
  );
}
