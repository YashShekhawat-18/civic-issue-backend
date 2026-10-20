"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import RoadTracker from "@/components/RoadTracker";
import StatusPill from "@/components/StatusPill";
import MapView from "@/components/MapViewLoader";
import ResolveForm from "@/components/ResolveForm";
import Alert from "@/components/Alert";
import Spinner from "@/components/Spinner";
import { photoSrc } from "@/lib/config";
import { formatDateTime, plural } from "@/lib/format";
import { btnGhost, btnPrimary, plate } from "@/lib/ui";
import { IconCheck, IconThumb } from "@/components/icons";
import { useT } from "@/context/LanguageContext";

function StartWork({ id, onStarted }) {
  const t = useT();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function start() {
    setBusy(true);
    setError("");
    try {
      onStarted(await api.patch(`/worker/complaints/${id}/status`, { status: "IN_PROGRESS" }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className={`${plate} space-y-3 p-5`} aria-label={t("Take this job")}>
      <h2 className="text-lg font-bold">{t("Take this job")}</h2>
      <p className="text-sm text-asphalt-soft">{t("Starting work assigns the job to you and tells the citizen it is being fixed.")}</p>
      <Alert type="error">{error}</Alert>
      <button onClick={start} disabled={busy} className={`${btnPrimary} w-full !py-3 !text-base`}>
        {busy ? "Starting..." : "Start work"}
      </button>
    </section>
  );
}

export default function TaskDetailPage() {
  const t = useT();
  const { id } = useParams();
  const { data, error, loading, reload } = useApi(`/worker/complaints/${id}`);
  // After an action we show the answer from the server straight away.
  const [updated, setUpdated] = useState(null);
  const c = updated || data;

  if (loading && !c) return <Spinner />;
  if (error && !c)
    return (
      <div className="space-y-4">
        <Alert type="error">{error === "Complaint not found" ? "We could not find this complaint in your department." : error}</Alert>
        <Link href="/worker/tasks" className={btnGhost}>
          {t("Back to tasks")}
        </Link>
      </div>
    );

  const [lng, lat] = c.location.coordinates;
  const done = (next) => {
    setUpdated(next);
    reload();
  };

  return (
    <article className="space-y-5">
      <Link href="/worker/tasks" className={`${btnGhost} -ml-3`}>
        {t("Back to tasks")}
      </Link>

      <header>
        <p className="text-sm font-semibold text-asphalt-soft">{c.complaintNumber}</p>
        <h1 className="mt-0.5 text-3xl font-extrabold leading-tight">{c.title}</h1>
        <div className="mt-2">
          <StatusPill status={c.status} overdue={c.overdue} />
        </div>
      </header>

      <section className={`${plate} p-5 pt-6`} aria-label={t("Progress")}>
        <RoadTracker status={c.status} />
        {c.status === "RESOLVED" && c.resolvedAt && (
          <p className="mt-4 text-center text-sm text-asphalt-soft">Fixed on {formatDateTime(c.resolvedAt)}.</p>
        )}
      </section>

      {c.status === "SUBMITTED" && <StartWork id={c.id} onStarted={done} />}
      {c.status === "IN_PROGRESS" && <ResolveForm complaintId={c.id} spot={{ lat, lng }} onResolved={done} />}
      {c.status === "RESOLVED" && (
        <Alert type="success">{t("This job is finished. The citizen has been told.")}</Alert>
      )}

      <div className="grid gap-5 md:grid-cols-2">
        {c.photoUrl && (
          <figure>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={photoSrc(c.photoUrl)} alt={`Reported: ${c.title}`} className="h-72 w-full rounded-2xl border border-line object-cover" />
            <figcaption className="mt-1.5 flex items-center gap-1.5 text-xs font-medium text-asphalt-soft">
              {t("Reported photo")}
              {c.photoGeotagged && (
                <span className="inline-flex items-center gap-1 text-highway-deep" data-testid="geotag-badge">
                  <IconCheck size={13} /> Location verified from the photo
                </span>
              )}
            </figcaption>
          </figure>
        )}
        <MapView center={{ lat, lng }} zoom={16} markers={[{ id: c.id, lat, lng, status: c.status }]} label={t("Where the issue is")} height={288} />
      </div>

      {c.resolutionPhotoUrl && (
        <figure>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={photoSrc(c.resolutionPhotoUrl)} alt={t("After-fix photo")} className="h-72 w-full rounded-2xl border border-line object-cover md:w-1/2" />
          <figcaption className="mt-1.5 text-xs font-medium text-asphalt-soft">{t("After-fix photo")}</figcaption>
        </figure>
      )}

      <section className={`${plate} p-5`}>
        <h2 className="text-lg font-bold">{t("Details")}</h2>
        <p className="mt-2 whitespace-pre-line text-asphalt/90">{c.description}</p>
        <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="font-semibold text-asphalt-soft">{t("Category")}</dt>
            <dd className="mt-0.5 font-medium">{t(c.category?.name)}</dd>
          </div>
          <div>
            <dt className="font-semibold text-asphalt-soft">{t("Reported by")}</dt>
            <dd className="mt-0.5 font-medium">{c.reporter ? c.reporter.name : "Anonymous"}</dd>
          </div>
          <div>
            <dt className="font-semibold text-asphalt-soft">{t("Reported on")}</dt>
            <dd className="mt-0.5 font-medium">{formatDateTime(c.createdAt)}</dd>
          </div>
          <div>
            <dt className="font-semibold text-asphalt-soft">{t("Taken by")}</dt>
            <dd className="mt-0.5 font-medium">{c.assignedWorker ? c.assignedWorker.name : "Nobody yet"}</dd>
          </div>
          <div>
            <dt className="font-semibold text-asphalt-soft">{t("Support from neighbours")}</dt>
            <dd className="mt-0.5 flex items-center gap-1.5 font-medium">
              <IconThumb size={15} /> {plural(c.upvoteCount ?? 0, "upvote", "upvotes")}
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-asphalt-soft">{t("Coordinates")}</dt>
            <dd className="mt-0.5 font-medium">
              {lat.toFixed(5)}, {lng.toFixed(5)}
            </dd>
          </div>
        </dl>
      </section>
    </article>
  );
}
