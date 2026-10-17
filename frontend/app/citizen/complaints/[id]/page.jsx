"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useApi } from "@/hooks/useApi";
import RoadTracker from "@/components/RoadTracker";
import StatusPill from "@/components/StatusPill";
import MapView from "@/components/MapViewLoader";
import Alert from "@/components/Alert";
import Spinner from "@/components/Spinner";
import { photoSrc } from "@/lib/config";
import { formatDateTime, plural } from "@/lib/format";
import { statusInfo } from "@/lib/status";
import { btnGhost, plate } from "@/lib/ui";
import { IconThumb } from "@/components/icons";

export default function ComplaintDetailPage() {
  const { id } = useParams();
  const { data: c, error, loading } = useApi(`/complaints/${id}`);

  if (loading) return <Spinner />;
  if (error)
    return (
      <div className="space-y-4">
        <Alert type="error">{error === "Complaint not found" ? "We could not find this complaint. It may belong to someone else." : error}</Alert>
        <Link href="/citizen/complaints" className={btnGhost}>
          Back to my complaints
        </Link>
      </div>
    );

  const [lng, lat] = c.location.coordinates;
  const info = statusInfo(c.status);

  return (
    <article className="space-y-5">
      <Link href="/citizen/complaints" className={`${btnGhost} -ml-3`}>
        Back to my complaints
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
        <p className="mt-4 text-center text-sm text-asphalt-soft">
          {info.plain}.
          {c.status === "RESOLVED" && c.resolvedAt ? ` Fixed on ${formatDateTime(c.resolvedAt)}.` : ""}
        </p>
        {c.overdue && c.status !== "RESOLVED" && (
          <p className="mt-2 text-center text-sm font-semibold text-flag">
            This is taking longer than expected. The department has been alerted.
          </p>
        )}
      </section>

      <div className="grid gap-5 md:grid-cols-2">
        {c.photoUrl && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={photoSrc(c.photoUrl)} alt={`Photo of: ${c.title}`} className="h-72 w-full rounded-2xl border border-line object-cover" />
        )}
        <MapView center={{ lat, lng }} zoom={16} markers={[{ id: c.id, lat, lng, status: c.status }]} label="Where the issue is" height={288} />
      </div>

      <section className={`${plate} p-5`}>
        <h2 className="text-lg font-bold">What you reported</h2>
        <p className="mt-2 whitespace-pre-line text-asphalt/90">{c.description}</p>
        <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="font-semibold text-asphalt-soft">Category</dt>
            <dd className="mt-0.5 font-medium">{c.category?.name}</dd>
          </div>
          <div>
            <dt className="font-semibold text-asphalt-soft">Handled by</dt>
            <dd className="mt-0.5 font-medium">{c.department?.name}</dd>
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
        {c.isAnonymous && <p className="mt-4 text-xs text-asphalt-soft">Your name is hidden from other citizens on this complaint.</p>}
      </section>
    </article>
  );
}
