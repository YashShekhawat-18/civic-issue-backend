"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { IconThumb } from "./icons";
import { plural } from "@/lib/format";
import { useT } from "@/context/LanguageContext";

/** Upvote / remove upvote for someone else's complaint. */
export default function UpvoteButton({ complaintId, initialCount, initialUpvoted, onChange }) {
  const t = useT();
  const [count, setCount] = useState(initialCount);
  const [upvoted, setUpvoted] = useState(initialUpvoted);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function toggle() {
    setBusy(true);
    setError("");
    try {
      const res = upvoted
        ? await api.delete(`/complaints/${complaintId}/upvote`)
        : await api.post(`/complaints/${complaintId}/upvote`);
      setUpvoted(res.hasUpvoted);
      setCount(res.upvoteCount);
      onChange?.(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={toggle}
        disabled={busy}
        aria-pressed={upvoted}
        className={`inline-flex items-center gap-2 rounded-lg border px-3.5 py-2 text-sm font-semibold transition-colors disabled:opacity-60 ${
          upvoted
            ? "border-highway bg-highway-tint text-highway-deep"
            : "border-line bg-white text-asphalt hover:bg-concrete"
        }`}
      >
        <IconThumb size={16} />
        {upvoted ? t("Upvoted") : t("Upvote")}
        <span className="font-normal text-asphalt-soft">{plural(count, "person", "people")}</span>
      </button>
      {error && <p className="mt-1 text-xs font-medium text-flag">{error}</p>}
    </div>
  );
}
