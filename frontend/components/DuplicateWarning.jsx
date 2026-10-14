"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { photoSrc } from "@/lib/config";
import Alert from "./Alert";

/**
 * Shown when the backend answers "a similar complaint already exists nearby" (nothing was created).
 * `result` is the backend's duplicate payload: {message, existingComplaint, canUpvote}.
 */
export default function DuplicateWarning({ result, onBack }) {
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
    <div className="mx-auto max-w-2xl rounded-lg border border-amber-300 bg-amber-50 p-6">
      <h1 className="text-xl font-bold text-amber-900">This issue may already be reported</h1>
      <p className="mt-1 text-sm text-amber-900">{result.message}</p>

      <div className="mt-4 flex gap-4 rounded-md border border-amber-200 bg-white p-3">
        {existing.photoUrl && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={photoSrc(existing.photoUrl)} alt="Existing complaint" className="h-24 w-24 rounded object-cover" />
        )}
        <div className="min-w-0 text-sm">
          <p className="font-semibold">{existing.title}</p>
          <p className="text-slate-600">
            {existing.complaintNumber} · {existing.status.replaceAll("_", " ")}
            {existing.distanceMeters != null && ` · about ${existing.distanceMeters} m away`}
          </p>
          <p className="mt-1 text-slate-600" data-testid="upvote-count">
            {count} {count === 1 ? "person has" : "people have"} upvoted this
          </p>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        <Alert type="error">{error}</Alert>
        {upvoted && !existing.isOwnComplaint && <Alert type="success">Thanks! Your upvote was added.</Alert>}
        <div className="flex flex-wrap gap-3">
          {canUpvote && (
            <button
              onClick={upvote}
              disabled={busy}
              className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-60"
            >
              {busy ? "Upvoting..." : "Upvote this complaint"}
            </button>
          )}
          <button onClick={onBack} className="rounded-md border border-slate-300 bg-white px-4 py-2 hover:bg-slate-100">
            Back to the form
          </button>
          <Link href="/citizen" className="rounded-md px-4 py-2 text-blue-700 hover:underline">
            Done
          </Link>
        </div>
      </div>
    </div>
  );
}
