import Link from "next/link";
import RoadTracker from "./RoadTracker";
import StatusPill from "./StatusPill";
import { IconThumb } from "./icons";
import { photoSrc } from "@/lib/config";
import { formatDate, plural } from "@/lib/format";
import { plate } from "@/lib/ui";

export default function ComplaintCard({ complaint: c }) {
  return (
    <Link
      href={`/citizen/complaints/${c.id}`}
      className={`${plate} block min-w-0 p-4 transition-shadow hover:shadow-md`}
    >
      <div className="flex gap-3">
        {c.photoUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={photoSrc(c.photoUrl)} alt="" className="h-16 w-16 shrink-0 rounded-lg object-cover" />
        ) : (
          <div className="h-16 w-16 shrink-0 rounded-lg bg-concrete" />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <h3 className="truncate text-base font-bold">{c.title}</h3>
            <StatusPill status={c.status} overdue={c.overdue} />
          </div>
          <p className="mt-0.5 truncate text-sm text-asphalt-soft">
            {c.category?.name} on {formatDate(c.createdAt)}
          </p>
          <p className="mt-0.5 flex items-center gap-1.5 text-xs text-asphalt-soft">
            <span className="font-semibold text-asphalt">{c.complaintNumber}</span>
            <span className="inline-flex items-center gap-1">
              <IconThumb size={13} /> {plural(c.upvoteCount ?? 0, "upvote", "upvotes")}
            </span>
          </p>
        </div>
      </div>
      <div className="mt-4 px-1">
        <RoadTracker status={c.status} compact />
      </div>
    </Link>
  );
}
