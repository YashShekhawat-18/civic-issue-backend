"use client";

import { LANGUAGES } from "@/lib/i18n";
import { useLanguage, useT } from "@/context/LanguageContext";

// Small English / Hindi toggle for the top bar.
export default function LanguageSwitch() {
  const { lang, setLang } = useLanguage();
  const t = useT();
  return (
    <div role="group" aria-label={t("Language")} className="flex rounded-lg bg-white/10 p-0.5 text-xs font-bold">
      {LANGUAGES.map((l) => (
        <button
          key={l.code}
          type="button"
          onClick={() => setLang(l.code)}
          aria-pressed={lang === l.code}
          aria-label={l.label}
          className={`rounded-md px-2 py-1 ${lang === l.code ? "bg-signal text-asphalt" : "text-white/80 hover:bg-white/10"}`}
        >
          {l.short}
        </button>
      ))}
    </div>
  );
}
