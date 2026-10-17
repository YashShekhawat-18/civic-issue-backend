export default function Spinner({ label = "Loading..." }) {
  return (
    <div role="status" className="flex items-center justify-center gap-3 p-10 text-asphalt-soft">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-line border-t-highway" />
      <span>{label}</span>
    </div>
  );
}
