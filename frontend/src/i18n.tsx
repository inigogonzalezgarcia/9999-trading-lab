import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { STRINGS, type Lang, type StringKey } from './locales';

export type { Lang };

const KEY = 'fxlab.lang';

function initial(): Lang {
  try {
    const saved = window.localStorage.getItem(KEY);
    if (saved === 'es' || saved === 'en') return saved;
  } catch {
    /* storage unavailable */
  }
  return navigator.language.toLowerCase().startsWith('es') ? 'es' : 'en';
}

const LangContext = createContext<{ lang: Lang; setLang: (lang: Lang) => void }>({ lang: 'en', setLang: () => undefined });

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initial);
  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    document.documentElement.lang = next;
    try {
      window.localStorage.setItem(KEY, next);
    } catch {
      /* ignore */
    }
  }, []);
  const value = useMemo(() => ({ lang, setLang }), [lang, setLang]);
  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

/** t('key') for UI strings; pick({es, en}) for content objects. */
export function useT() {
  const { lang, setLang } = useContext(LangContext);
  const t = useCallback((key: StringKey, vars?: Record<string, string | number>) => {
    let text: string = STRINGS[key]?.[lang] ?? STRINGS[key]?.en ?? key;
    if (vars) Object.entries(vars).forEach(([name, value]) => { text = text.replace(`{${name}}`, String(value)); });
    return text;
  }, [lang]);
  const pick = useCallback(<T,>(value: { es: T; en: T } | T | undefined): T | undefined => {
    if (value && typeof value === 'object' && 'es' in (value as object) && 'en' in (value as object)) return (value as { es: T; en: T })[lang];
    return value as T | undefined;
  }, [lang]);
  return { t, pick, lang, setLang };
}
