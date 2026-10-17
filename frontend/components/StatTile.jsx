import Link from "next/link";
import { compact } from "@/lib/charts";
import { plate } from "@/lib/ui";

// A headline number that is also a shortcut to the matching list.
export default function StatTile({ id, label, value, href, tone = "text-asphalt" }) {
  return (
    <Link href={href} className={`${plate} block p-4 transition-shadow hover:shadow-md`}>
      <p className="text-sm font-semibold text-asphalt-soft">{label}</p>
      <p className={`mt-1 text-3xl font-extrabold ${tone}`} data-testid={`stat-${id}`}>
        {compact(value)}
      </p>
    </Link>
  );
}
