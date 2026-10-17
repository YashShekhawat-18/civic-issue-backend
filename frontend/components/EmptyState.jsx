import Link from "next/link";
import { btnPrimary } from "@/lib/ui";

// An empty screen should say what to do next.
export default function EmptyState({ title, text, actionHref, actionLabel }) {
  return (
    <div className="rounded-2xl border border-dashed border-line bg-white/60 px-6 py-12 text-center">
      <h2 className="text-lg font-bold">{title}</h2>
      {text && <p className="mx-auto mt-1 max-w-sm text-sm text-asphalt-soft">{text}</p>}
      {actionHref && (
        <Link href={actionHref} className={`${btnPrimary} mt-5`}>
          {actionLabel}
        </Link>
      )}
    </div>
  );
}
