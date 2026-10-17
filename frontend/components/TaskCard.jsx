import Link from "next/link";
import StatusPill from "./StatusPill";
import { IconThumb } from "./icons";
import { photoSrc } from "@/lib/config";
import { timeAgo, plural } from "@/lib/format";
import { plate } from "@/lib/ui";

// One job in the worker's list.
// base: where the card links to. showDepartment: admins see every department.
export default function TaskCard({ task: t, base = "/worker/tasks", showDepartment = false }) {
  return (
    <Link href={`${base}/${t.id}`} className={`${plate} flex min-w-0 gap-3 p-4 transition-shadow hover:shadow-md`}>
      {t.photoUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={photoSrc(t.photoUrl)} alt="" className="h-16 w-16 shrink-0 rounded-lg object-cover" />
      ) : (
        <div className="h-16 w-16 shrink-0 rounded-lg bg-concrete" />
      )}
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <h3 className="truncate text-base font-bold">{t.title}</h3>
          <StatusPill status={t.status} overdue={t.overdue} />
        </div>
        <p className="mt-0.5 truncate text-sm text-asphalt-soft">
          {t.category?.name}{showDepartment && t.department ? ` in ${t.department.name}` : ""}, reported {timeAgo(t.createdAt)}
        </p>
        <p className="mt-0.5 flex flex-wrap items-center gap-x-3 text-xs text-asphalt-soft">
          <span className="font-semibold text-asphalt">{t.complaintNumber}</span>
          <span className="inline-flex items-center gap-1">
            <IconThumb size={13} /> {plural(t.upvoteCount ?? 0, "upvote", "upvotes")}
          </span>
          {t.assignedWorker && <span>Taken by {t.assignedWorker.name}</span>}
          {typeof t.ageDays === "number" && <span className="font-semibold text-flag">{plural(t.ageDays, "day", "days")} old</span>}
        </p>
      </div>
    </Link>
  );
}
