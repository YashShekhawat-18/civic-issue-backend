"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import RoadTracker from "@/components/RoadTracker";
import StatusPill from "@/components/StatusPill";
import MapView from "@/components/MapViewLoader";
import Alert from "@/components/Alert";
import Spinner from "@/components/Spinner";
import { photoSrc } from "@/lib/config";
import { formatDateTime, plural } from "@/lib/format";
import { statusInfo } from "@/lib/status";
import { btnGhost, btnPrimary, btnSecondary, plate } from "@/lib/ui";
import { IconCheck, IconThumb } from "@/components/icons";

const PRIORITIES = [
  { value: "LOW", label: "Low" },
  { value: "MEDIUM", label: "Medium" },
  { value: "HIGH", label: "High" },
];

// Admin override: moves the complaint to its next status. No photo is needed (workers need one to resolve).
function StatusControl({ complaint, onChanged }) {
  const next = complaint.allowedNextStatuses?.[0];
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (!next) return <Alert type="success">This complaint is resolved. Its status can no longer change.</Alert>;

  async function change() {
    setBusy(true);
    setError("");
    try {
      await api.patch(`/complaints/${complaint.id}/status`, { status: next, ...(note.trim() ? { note: note.trim() } : {}) });
      setNote("");
      onChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={`${plate} space-y-3 p-5`} aria-label="Change status">
      <h2 className="text-lg font-bold">Change status</h2>
      <p className="text-sm text-asphalt-soft">
        This tells the citizen by alert and email.{next === "RESOLVED" ? " As an admin you can resolve without an after-fix photo." : ""}
      </p>
      <Alert type="error">{error}</Alert>
      <label className="block text-sm font-semibold">
        Note for the citizen (optional)
        <textarea
          rows={2}
          maxLength={500}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          className="mt-1.5 w-full rounded-lg border border-line bg-white px-3.5 py-2.5 font-normal"
        />
      </label>
      <button onClick={change} disabled={busy} className={`${btnPrimary} w-full !py-3`}>
        {busy ? "Saving..." : `Mark as ${statusInfo(next).label.toLowerCase()}`}
      </button>
    </section>
  );
}

function PriorityControl({ complaint, onChanged }) {
  const [value, setValue] = useState(complaint.priority);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });

  async function save() {
    setBusy(true);
    setMessage({ type: "", text: "" });
    try {
      await api.patch(`/complaints/${complaint.id}`, { priority: value });
      setMessage({ type: "success", text: "Priority saved." });
      onChanged();
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-wrap items-end gap-2">
      <label className="text-sm font-semibold">
        Priority
        <select
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="mt-1 block rounded-lg border border-line bg-white px-3 py-2 font-normal"
        >
          {PRIORITIES.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </label>
      <button onClick={save} disabled={busy || value === complaint.priority} className={btnSecondary}>
        {busy ? "Saving..." : "Save priority"}
      </button>
      <span className="basis-full">
        <Alert type={message.type || "info"}>{message.text}</Alert>
      </span>
    </div>
  );
}

export default function AdminComplaintDetail() {
  const { id } = useParams();
  const { data, error, loading, reload } = useApi(`/admin/complaints/${id}`);
  const c = data;

  if (loading && !c) return <Spinner />;
  if (error && !c)
    return (
      <div className="space-y-4">
        <Alert type="error">{error}</Alert>
        <Link href="/admin/complaints" className={btnGhost}>
          Back to complaints
        </Link>
      </div>
    );

  const [lng, lat] = c.location.coordinates;

  return (
    <article className="space-y-5">
      <Link href="/admin/complaints" className={`${btnGhost} -ml-3`}>
        Back to complaints
      </Link>

      <header>
        <p className="text-sm font-semibold text-asphalt-soft">{c.complaintNumber}</p>
        <h1 className="mt-0.5 text-3xl font-extrabold leading-tight">{c.title}</h1>
        <div className="mt-2">
          <StatusPill status={c.status} overdue={c.overdue} />
        </div>
      </header>

      <section className={`${plate} p-5 pt-6`} aria-label="Progress">
        <RoadTracker status={c.status} />
        {c.status === "RESOLVED" && c.resolvedAt && (
          <p className="mt-4 text-center text-sm text-asphalt-soft">Fixed on {formatDateTime(c.resolvedAt)}.</p>
        )}
      </section>

      <StatusControl complaint={c} onChanged={reload} />

      <div className="grid gap-5 md:grid-cols-2">
        {c.photoUrl && (
          <figure>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={photoSrc(c.photoUrl)} alt={`Reported: ${c.title}`} className="h-72 w-full rounded-2xl border border-line object-cover" />
            <figcaption className="mt-1.5 flex items-center gap-1.5 text-xs font-medium text-asphalt-soft">
              Reported photo
              {c.photoGeotagged && (
                <span className="inline-flex items-center gap-1 text-highway-deep" data-testid="geotag-badge">
                  <IconCheck size={13} /> Location verified from the photo
                </span>
              )}
            </figcaption>
          </figure>
        )}
        <MapView center={{ lat, lng }} zoom={16} markers={[{ id: c.id, lat, lng, status: c.status }]} label="Where the issue is" height={288} />
      </div>

      {c.resolutionPhotoUrl && (
        <figure>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={photoSrc(c.resolutionPhotoUrl)} alt="After-fix photo" className="h-72 w-full rounded-2xl border border-line object-cover md:w-1/2" />
          <figcaption className="mt-1.5 text-xs font-medium text-asphalt-soft">After-fix photo from the worker</figcaption>
        </figure>
      )}

      <section className={`${plate} space-y-5 p-5`}>
        <div>
          <h2 className="text-lg font-bold">Details</h2>
          <p className="mt-2 whitespace-pre-line text-asphalt/90">{c.description}</p>
        </div>
        <dl className="grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="font-semibold text-asphalt-soft">Category</dt>
            <dd className="mt-0.5 font-medium">{c.category?.name}</dd>
          </div>
          <div>
            <dt className="font-semibold text-asphalt-soft">Department</dt>
            <dd className="mt-0.5 font-medium">{c.department?.name}</dd>
          </div>
          <div>
            <dt className="font-semibold text-asphalt-soft">Reported by</dt>
            <dd className="mt-0.5 font-medium">{c.reporter ? c.reporter.name : "Anonymous"}</dd>
          </div>
          <div>
            <dt className="font-semibold text-asphalt-soft">Worker</dt>
            <dd className="mt-0.5 font-medium">{c.assignedWorker ? c.assignedWorker.name : "Nobody yet"}</dd>
          </div>
          <div>
            <dt className="font-semibold text-asphalt-soft">Reported on</dt>
            <dd className="mt-0.5 font-medium">{formatDateTime(c.createdAt)}</dd>
          </div>
          <div>
            <dt className="font-semibold text-asphalt-soft">Support from neighbours</dt>
            <dd className="mt-0.5 flex items-center gap-1.5 font-medium">
              <IconThumb size={15} /> {plural(c.upvoteCount ?? 0, "upvote", "upvotes")}
            </dd>
          </div>
        </dl>
        <PriorityControl key={c.priority} complaint={c} onChanged={reload} />
      </section>
    </article>
  );
}
