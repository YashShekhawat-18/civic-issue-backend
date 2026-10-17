import { btnSecondary } from "@/lib/ui";

// Previous / Next with a plain "Page 2 of 5". Used by every long admin list.
export default function Pagination({ page, limit, total, onChange }) {
  const pages = Math.max(1, Math.ceil(total / limit));
  if (pages <= 1) return null;
  return (
    <nav aria-label="Pages" className="mt-5 flex items-center justify-between gap-3">
      <button className={btnSecondary} disabled={page <= 1} onClick={() => onChange(page - 1)}>
        Previous
      </button>
      <p className="text-sm text-asphalt-soft">
        Page {page} of {pages} ({total} in all)
      </p>
      <button className={btnSecondary} disabled={page >= pages} onClick={() => onChange(page + 1)}>
        Next
      </button>
    </nav>
  );
}
