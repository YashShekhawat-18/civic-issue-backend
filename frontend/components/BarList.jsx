import { share } from "@/lib/charts";
import { plate } from "@/lib/ui";

/**
 * A ranked horizontal bar chart in plain HTML. One series, so one colour and no legend box:
 * the title says what is plotted. The value sits at the tip of each bar; hovering or focusing a
 * row shows the share of the total. "Show as table" gives the same numbers without hover.
 */
export default function BarList({ title, subtitle, rows, unit = "complaints" }) {
  const total = rows.reduce((sum, r) => sum + r.count, 0);
  const max = Math.max(1, ...rows.map((r) => r.count));

  return (
    <section className={`${plate} p-5`} aria-label={title}>
      <h2 className="text-lg font-bold">{title}</h2>
      {subtitle && <p className="text-sm text-asphalt-soft">{subtitle}</p>}

      {rows.length === 0 ? (
        <p className="mt-4 text-sm text-asphalt-soft">Nothing to show yet.</p>
      ) : (
        <ul className="mt-4 space-y-2.5">
          {rows.map((r) => (
            <li
              key={r.id}
              tabIndex={0}
              aria-label={`${r.name}: ${r.count} ${unit}, ${share(r.count, total)}% of all`}
              className="group relative rounded-md outline-none focus-visible:ring-2 focus-visible:ring-sign"
            >
              <div className="mb-1 flex items-baseline justify-between gap-3 text-sm">
                <span className="min-w-0 truncate font-medium">{r.name}</span>
                <span className="font-bold tabular-nums">{r.count}</span>
              </div>
              <div className="h-3 w-full rounded-full bg-concrete">
                <div
                  data-testid="bar"
                  className="h-3 rounded-r-[4px] rounded-l-none bg-highway transition-[filter] group-hover:brightness-125 group-focus-visible:brightness-125"
                  style={{ width: `${Math.max(2, (r.count / max) * 100)}%` }}
                />
              </div>
              <span
                role="tooltip"
                className="pointer-events-none absolute -top-7 right-0 z-10 hidden whitespace-nowrap rounded-md bg-asphalt px-2.5 py-1 text-xs text-white shadow group-hover:block group-focus-visible:block"
              >
                <strong>{r.count}</strong> {unit}, {share(r.count, total)}% of all
              </span>
            </li>
          ))}
        </ul>
      )}

      {rows.length > 0 && (
        <details className="mt-4 text-sm">
          <summary className="cursor-pointer font-semibold text-sign">Show as table</summary>
          <table className="mt-2 w-full text-left">
            <thead>
              <tr className="text-asphalt-soft">
                <th className="py-1 font-semibold">Name</th>
                <th className="py-1 text-right font-semibold">Complaints</th>
                <th className="py-1 text-right font-semibold">Share</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-t border-line">
                  <td className="py-1">{r.name}</td>
                  <td className="py-1 text-right tabular-nums">{r.count}</td>
                  <td className="py-1 text-right tabular-nums">{share(r.count, total)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </section>
  );
}
