"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { setCurrentLang, translate } from "@/lib/i18n";

const LanguageContext = createContext(null);
const KEY = "civic_lang";

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState("en");

  // Restore the saved choice after the first render (keeps server and browser output identical).
  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(KEY);
      // eslint-disable-next-line react-hooks/set-state-in-effect -- must run after hydration
      if (saved === "hi" || saved === "en") setLangState(saved);
    } catch {
      /* storage blocked: stay on English */
    }
  }, []);

  // Set during render (not in an effect) so child pages already format dates in the right language.
  setCurrentLang(lang);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((code) => {
    setLangState(code);
    try {
      window.localStorage.setItem(KEY, code);
    } catch {
      /* ignore */
    }
  }, []);

  const value = useMemo(() => ({ lang, setLang }), [lang, setLang]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  return useContext(LanguageContext) || { lang: "en", setLang: () => {} };
}

// const t = useT();  t("Home")  t("Hello, {name}", { name })
export function useT() {
  const { lang } = useLanguage();
  return useCallback((text, vars) => translate(lang, text, vars), [lang]);
}
