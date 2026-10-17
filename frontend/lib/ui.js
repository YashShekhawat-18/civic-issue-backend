// Shared class names so every button and card looks the same.
const base =
  "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60";

export const btnPrimary = `${base} bg-highway text-white hover:bg-highway-deep`;
export const btnSecondary = `${base} border border-line bg-white text-asphalt hover:bg-concrete`;
export const btnSignal = `${base} bg-signal text-asphalt hover:brightness-95`;
export const btnGhost = `${base} text-sign hover:bg-sign-tint`;

// A "plate": white panel with a thin border. Used sparingly; not everything needs one.
export const plate = "rounded-2xl border border-line bg-white";
