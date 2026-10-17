export default function ActiveBadge({ active }) {
  return active ? (
    <span className="rounded-full bg-highway-tint px-2.5 py-0.5 text-xs font-semibold text-highway-deep">Active</span>
  ) : (
    <span className="rounded-full bg-concrete px-2.5 py-0.5 text-xs font-semibold text-asphalt-soft">Inactive</span>
  );
}
