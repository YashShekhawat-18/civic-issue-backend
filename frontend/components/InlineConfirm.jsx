"use client";

import { useState } from "react";
import { btnGhost, btnSecondary } from "@/lib/ui";
import { useT } from "@/context/LanguageContext";

// A risky button that asks "are you sure?" in place, instead of a pop-up.
export default function InlineConfirm({ label, confirmLabel, onConfirm, disabled }) {
  const t = useT();
  const [asking, setAsking] = useState(false);
  if (!asking)
    return (
      <button type="button" className={`${btnGhost} !text-flag hover:!bg-flag-tint`} disabled={disabled} onClick={() => setAsking(true)}>
        {label}
      </button>
    );
  return (
    <span className="inline-flex items-center gap-2">
      <button
        type="button"
        className="inline-flex items-center rounded-lg bg-flag px-3 py-2 text-sm font-semibold text-white hover:brightness-95"
        onClick={() => { setAsking(false); onConfirm(); }}
      >
        {confirmLabel}
      </button>
      <button type="button" className={btnSecondary} onClick={() => setAsking(false)}>{t("Cancel")}</button>
    </span>
  );
}
