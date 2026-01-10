// components/Header.tsx
"use client";

import Link from "next/link";
import Image from "next/image";

interface HeaderProps {
  showSettings?: boolean;
  showBack?: boolean;
}

export function Header({ showSettings = true, showBack = false }: HeaderProps) {
  return (
    <header className="bg-white/95 backdrop-blur-sm border-b border-gray-200 -mx-4 px-4 py-3 mb-8 sticky top-0 z-40">
      <div className="flex items-center justify-between max-w-6xl mx-auto">
        <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
          <Image src="/logo.png" alt="TranscribeFlow" width={40} height={40} />
          <span className="text-xl tracking-wide uppercase">
            <span className="font-bold" style={{ color: "#1a365d" }}>Transcribe</span>
            <span className="font-normal" style={{ color: "#2d4a6f" }}>Flow</span>
          </span>
        </Link>
        <div className="flex items-center gap-4">
          {showBack && (
            <Link href="/" className="text-sm text-gray-600 hover:text-gray-900">
              &larr; Back
            </Link>
          )}
          {showSettings && (
            <Link href="/settings" className="text-sm text-gray-600 hover:text-gray-900">
              Settings
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
