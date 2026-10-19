"use client";

import { useT } from "@/context/LanguageContext";
import { btnSecondary } from "@/lib/ui";

// Previous / Next with a plain "Page 2 of 5". Used by every long admin list.
export default function Pagination({ page, limit, total, onChange }) {
  const t = useT();
  const pages = Math.max(1, Math.ceil(total / limit));
  if (pages <= 1) return null;
  return (
    <nav aria-label={t("Pages")} className="mt-5 flex items-center justify-between gap-3">
      <button className={btnSecondary} disabled={page <= 1} onClick={() => onChange(page - 1)}>
        {t("Previous")}
      </button>
      <p className="text-sm text-asphalt-soft">
        {t("Page {page} of {pages} ({total} in all)", { page, pages, total })}
      </p>
      <button className={btnSecondary} disabled={page >= pages} onClick={() => onChange(page + 1)}>
        {t("Next")}
      </button>
    </nav>
  );
}
