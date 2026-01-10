import type { Locale } from './config';

// Import all English messages
import enCommon from './messages/en/common.json';
import enUpload from './messages/en/upload.json';
import enQueue from './messages/en/queue.json';
import enSettings from './messages/en/settings.json';
import enTranscription from './messages/en/transcription.json';
import enInsights from './messages/en/insights.json';

// Import all Russian messages
import ruCommon from './messages/ru/common.json';
import ruUpload from './messages/ru/upload.json';
import ruQueue from './messages/ru/queue.json';
import ruSettings from './messages/ru/settings.json';
import ruTranscription from './messages/ru/transcription.json';
import ruInsights from './messages/ru/insights.json';

const messages: Record<Locale, Record<string, string>> = {
  en: {
    ...enCommon,
    ...enUpload,
    ...enQueue,
    ...enSettings,
    ...enTranscription,
    ...enInsights,
  },
  ru: {
    ...ruCommon,
    ...ruUpload,
    ...ruQueue,
    ...ruSettings,
    ...ruTranscription,
    ...ruInsights,
  },
};

export function getMessages(locale: Locale): Record<string, string> {
  return messages[locale];
}
