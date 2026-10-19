import { getCurrentLang, translate } from "./i18n";

// Dates follow the chosen language (month names in Hindi). The "-u-nu-latn" part keeps
// ordinary 0-9 digits so numbers look the same in both languages.
const cache = {};
function formatter(kind) {
  const lang = getCurrentLang();
  const key = `${kind}|${lang}`;
  if (!cache[key]) {
    const locale = `${lang === "hi" ? "hi-IN" : "en-IN"}-u-nu-latn`;
    cache[key] = new Intl.DateTimeFormat(
      locale,
      kind === "date"
        ? { day: "numeric", month: "short", year: "numeric" }
        : { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }
    );
  }
  return cache[key];
}

export function formatDate(value) {
  if (!value) return "";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? "" : formatter("date").format(d);
}

export function formatDateTime(value) {
  if (!value) return "";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? "" : formatter("time").format(d);
}

// "5 minutes ago", "3 days ago", or the date for anything older than a month.
export function timeAgo(value, now = Date.now()) {
  if (!value) return "";
  const lang = getCurrentLang();
  const t = (text, vars) => translate(lang, text, vars);
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) return "";
  const seconds = Math.max(0, Math.round((now - then) / 1000));
  if (seconds < 60) return t("just now");
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return t(minutes === 1 ? "{n} minute ago" : "{n} minutes ago", { n: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return t(hours === 1 ? "{n} hour ago" : "{n} hours ago", { n: hours });
  const days = Math.floor(hours / 24);
  if (days < 30) return t(days === 1 ? "{n} day ago" : "{n} days ago", { n: days });
  return formatDate(value);
}

// plural(3, "upvote", "upvotes") -> "3 upvotes" (or its Hindi form when a translation exists)
export function plural(n, one, many) {
  return translate(getCurrentLang(), `{n} ${n === 1 ? one : many}`, { n });
}
