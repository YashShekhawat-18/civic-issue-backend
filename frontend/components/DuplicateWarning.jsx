"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { photoSrc } from "@/lib/config";
import { statusInfo } from "@/lib/status";
import { btnGhost, btnPrimary, btnSecondary } from "@/lib/ui";
import { useT } from "@/context/LanguageContext";
import Alert from "./Alert";
import StatusPill from "./StatusPill";

/**
 * Shown when the backend answers "a similar complaint already exists nearby" (nothing was created).
 * `result` is the backend's duplicate payload: {message, existingComplaint, canUpvote}.
 */
export default function DuplicateWarning({ result, onBack }) {
  const t = useT();
  const existing = result.existingComplaint;
  const [upvoted, setUpvoted] = useState(existing.hasUpvoted);
  const [count, setCount] = useState(existing.upvoteCount);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function upvote() {
    setBusy(true);
    setError("");
    try {
      const res = await api.post(`/complaints/${existing.id}/upvote`);
      setUpvoted(true);
      setCount(res.upvoteCount);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const canUpvote = result.canUpvote && !upvoted;

  return (
    <div className="mx-auto max-w-2xl overflow-hidden rounded-2xl border border-signal bg-white">
      <div className="bg-signal px-6 py-4">
        <h1 className="text-2xl font-extrabold">{t("This issue may already be reported")}</h1>
        <p className="mt-1 text-sm font-medium text-asphalt/80">{result.message}</p>
      </div>

      <div className="space-y-4 p-6">
        <div className="flex gap-4 rounded-xl border border-line p-3">
          {existing.photoUrl && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={photoSrc(existing.photoUrl)} alt={t("Existing complaint")} className="h-24 w-24 shrink-0 rounded-lg object-cover" />
          )}
          <div className="min-w-0 text-sm">
            <p className="text-base font-bold">{existing.title}</p>
            <p className="mt-0.5 text-asphalt-soft">
              {existing.complaintNumber}
              {existing.distanceMeters != null && `, ${t("about {n} m from your pin", { n: existing.distanceMeters })}`}
            </p>
            <div className="mt-1.5">
              <StatusPill status={existing.status} overdue={existing.overdue} />
              <span className="sr-only">{statusInfo(existing.status).plain}</span>
            </div>
            <p className="mt-1.5 text-asphalt-soft" data-testid="upvote-count">
              {t(count === 1 ? "{n} person has upvoted this" : "{n} people have upvoted this", { n: count })}
            </p>
          </div>
        </div>

        <Alert type="error">{error}</Alert>
        {upvoted && !existing.isOwnComplaint && <Alert type="success">{t("Thanks! Your upvote was added.")}</Alert>}

        <div className="flex flex-wrap gap-3">
          {canUpvote && (
            <button onClick={upvote} disabled={busy} className={btnPrimary}>
              {busy ? t("Upvoting...") : t("Upvote this complaint")}
            </button>
          )}
          <button onClick={onBack} className={btnSecondary}>
            {t("Back to the form")}
          </button>
          <Link href="/citizen" className={btnGhost}>
            {t("Done")}
          </Link>
        </div>
      </div>
    </div>
  );
}
