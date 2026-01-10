'use client';

import { useLocale, type Locale } from '@/i18n';
import { cn } from '@/lib/utils';

const LOCALE_LABELS: Record<Locale, string> = {
  en: 'EN',
  ru: 'RU',
};

const LOCALES: Locale[] = ['en', 'ru'];

export function LanguageSwitcher() {
  const { locale, setLocale } = useLocale();

  return (
    <div className="flex items-center gap-0.5 rounded-md border border-gray-200 p-0.5 bg-white">
      {LOCALES.map((code) => (
        <button
          key={code}
          onClick={() => setLocale(code)}
          className={cn(
            'px-2 py-1 text-xs font-medium rounded transition-colors',
            locale === code
              ? 'bg-gray-900 text-white'
              : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'
          )}
        >
          {LOCALE_LABELS[code]}
        </button>
      ))}
    </div>
  );
}
