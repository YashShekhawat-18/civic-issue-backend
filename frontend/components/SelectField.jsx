// A labelled <select>, styled like FormField.
export default function SelectField({ id, label, error, children, ...props }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-semibold text-asphalt">{label}</label>
      <select
        id={id}
        name={id}
        aria-invalid={error ? "true" : "false"}
        className={`w-full rounded-lg border bg-white px-3 py-2.5 text-asphalt ${error ? "border-flag" : "border-line hover:border-asphalt-soft/50"}`}
        {...props}
      >
        {children}
      </select>
      {error && <p className="mt-1.5 text-xs font-medium text-flag">{error}</p>}
    </div>
  );
}
