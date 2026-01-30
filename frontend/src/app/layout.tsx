import type { Metadata } from "next";
import localFont from "next/font/local";
import { Toaster } from "sonner";
import { LocaleProvider } from "@/i18n";
import { SystemMonitorWrapper } from "@/components/SystemMonitorWrapper";
import "./globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "TranscribeFlow",
  description: "Local AI-powered meeting transcription with speaker diarization and intelligent insights",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <LocaleProvider>
          {/* Fixed-width wrapper prevents layout shift from Radix scroll lock */}
          <div className="content-wrapper">
            {children}
          </div>
          <Toaster richColors position="top-right" />
          <SystemMonitorWrapper />
        </LocaleProvider>
      </body>
    </html>
  );
}
