import { IconCheck, IconFlag, IconWrench } from "./icons";
import { STATUS_ORDER, statusIndex, statusInfo } from "@/lib/status";

/**
 * The signature element: a complaint's progress drawn as a road with three stops.
 * Green = the stretch already travelled. The amber stop is where the complaint is now.
 */
export default function RoadTracker({ status, compact = false }) {
  const current = statusIndex(status);
  const finished = status === "RESOLVED";
  const nodeSize = compact ? "h-6 w-6" : "h-8 w-8";
  const icons = [IconCheck, IconWrench, IconFlag];

  return (
    <div
      role="img"
      aria-label={`Progress: ${statusInfo(status).label}. ${statusInfo(status).plain}.`}
      className="relative select-none"
    >
      {/* the road */}
      <div
        className="absolute left-[16.667%] right-[16.667%] -translate-y-1/2 rounded-full bg-asphalt"
        style={{ top: compact ? 12 : 16, height: compact ? 6 : 8 }}
      >
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-highway"
          style={{ width: `${(current / (STATUS_ORDER.length - 1)) * 100}%` }}
        />
        <div
          className="absolute inset-x-2 top-1/2 h-px -translate-y-1/2 opacity-60"
          style={{ backgroundImage: "repeating-linear-gradient(90deg,#fff 0 5px,transparent 5px 11px)" }}
        />
      </div>

      <ol className="relative grid grid-cols-3">
        {STATUS_ORDER.map((s, i) => {
          const done = i < current || (finished && i === current);
          const active = i === current && !finished;
          const Icon = done ? IconCheck : icons[i];
          return (
            <li key={s} className="flex flex-col items-center gap-1.5 text-center">
              <span
                className={`flex ${nodeSize} items-center justify-center rounded-full border-2 ${
                  done
                    ? "border-highway bg-highway text-white"
                    : active
                      ? "border-signal bg-signal text-asphalt ring-4 ring-signal/30"
                      : "border-line bg-white text-asphalt-soft"
                }`}
              >
                <Icon size={compact ? 13 : 16} />
              </span>
              <span
                className={`${compact ? "text-[11px]" : "text-xs"} leading-tight ${
                  i === current ? "font-bold text-asphalt" : "text-asphalt-soft"
                }`}
              >
                {statusInfo(s).label}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
