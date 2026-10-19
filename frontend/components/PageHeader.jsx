"use client";

import { useT } from "@/context/LanguageContext";

export default function PageHeader({ title, children }) {
  const t = useT();
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <h1 className="text-3xl font-extrabold leading-tight">{t(title)}</h1>
      {children}
    </div>
  );
}
