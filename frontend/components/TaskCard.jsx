"use client";

import Link from "next/link";
import { useT } from "@/context/LanguageContext";
import StatusPill from "./StatusPill";
import { IconThumb } from "./icons";
import { photoSrc } from "@/lib/config";
import { timeAgo, plural } from "@/lib/format";
import { plate } from "@/lib/ui";

// One job in the worker's list.
// base: where the card links to. showDepartment: admins see every department.
export default function TaskCard({ task, base = "/worker/tasks", showDepartment = false }) {
  const t = useT();
  return (
    <Link href={`${base}/${task.id}`} className={`${plate} flex min-w-0 gap-3 p-4 transition-shadow hover:shadow-md`}>
      {task.photoUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={photoSrc(task.photoUrl)} alt="" className="h-16 w-16 shrink-0 rounded-lg object-cover" />
      ) : (
        <div className="h-16 w-16 shrink-0 rounded-lg bg-concrete" />
      )}
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <h3 className="truncate text-base font-bold">{task.title}</h3>
          <StatusPill status={task.status} overdue={task.overdue} />
        </div>
        <p className="mt-0.5 truncate text-sm text-asphalt-soft">
          {t(task.category?.name)}{showDepartment && task.department ? ` ${t("in")} ${t(task.department.name)}` : ""}, {t("reported")} {timeAgo(task.createdAt)}
        </p>
        <p className="mt-0.5 flex flex-wrap items-center gap-x-3 text-xs text-asphalt-soft">
          <span className="font-semibold text-asphalt">{task.complaintNumber}</span>
          <span className="inline-flex items-center gap-1">
            <IconThumb size={13} /> {plural(task.upvoteCount ?? 0, "upvote", "upvotes")}
          </span>
          {task.assignedWorker && <span>{t("Taken by")} {task.assignedWorker.name}</span>}
          {typeof task.ageDays === "number" && <span className="font-semibold text-flag">{plural(task.ageDays, "day", "days")} {t("old")}</span>}
        </p>
      </div>
    </Link>
  );
}
