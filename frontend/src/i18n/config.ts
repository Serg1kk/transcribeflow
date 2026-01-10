export type Locale = 'en' | 'ru';

export const LOCALES: Locale[] = ['en', 'ru'];
export const DEFAULT_LOCALE: Locale = 'en';

export function detectLocale(): Locale {
  if (typeof window === 'undefined') return DEFAULT_LOCALE;

  // 1. Check localStorage first (user's explicit choice)
  const stored = localStorage.getItem('locale');
  if (stored === 'en' || stored === 'ru') return stored;

  // 2. Detect from browser
  const browserLang = navigator.language.toLowerCase();
  if (browserLang.startsWith('ru')) return 'ru';

  return DEFAULT_LOCALE;
}

export function setStoredLocale(locale: Locale): void {
  localStorage.setItem('locale', locale);
}
