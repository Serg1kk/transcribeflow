'use client';

import { createContext, useState, useEffect, useCallback, useMemo } from 'react';
import { IntlProvider } from 'react-intl';
import { type Locale, DEFAULT_LOCALE, detectLocale, setStoredLocale } from './config';
import { getMessages } from './messages';

interface LocaleContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
}

export const LocaleContext = createContext<LocaleContextType>({
  locale: DEFAULT_LOCALE,
  setLocale: () => {},
});

interface LocaleProviderProps {
  children: React.ReactNode;
}

export function LocaleProvider({ children }: LocaleProviderProps) {
  const [locale, setLocaleState] = useState<Locale>(DEFAULT_LOCALE);
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
    const detected = detectLocale();
    setLocaleState(detected);
  }, []);

  const setLocale = useCallback((newLocale: Locale) => {
    setStoredLocale(newLocale);
    setLocaleState(newLocale);
  }, []);

  const messages = useMemo(() => getMessages(locale), [locale]);

  const contextValue = useMemo(() => ({ locale, setLocale }), [locale, setLocale]);

  // Prevent hydration mismatch by using default locale on server
  const effectiveLocale = isClient ? locale : DEFAULT_LOCALE;
  const effectiveMessages = isClient ? messages : getMessages(DEFAULT_LOCALE);

  return (
    <LocaleContext.Provider value={contextValue}>
      <IntlProvider
        locale={effectiveLocale}
        messages={effectiveMessages}
        onError={(err) => {
          // Ignore missing translation errors in development
          if (err.code === 'MISSING_TRANSLATION') {
            console.warn('Missing translation:', err.message);
            return;
          }
          console.error(err);
        }}
      >
        {children}
      </IntlProvider>
    </LocaleContext.Provider>
  );
}
