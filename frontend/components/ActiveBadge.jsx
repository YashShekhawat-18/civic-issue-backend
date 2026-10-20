"use client";

import { useT } from "@/context/LanguageContext";
export default function ActiveBadge({ active }) {
  const t = useT();
  return active ? (
    <span className="rounded-full bg-highway-tint px-2.5 py-0.5 text-xs font-semibold text-highway-deep">{t("Active")}</span>
  ) : (
    <span className="rounded-full bg-concrete px-2.5 py-0.5 text-xs font-semibold text-asphalt-soft">{t("Inactive")}</span>
  );
}
