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
    <div className="flex items-center justify-between mb-8">
      <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
        <Image src="/logo.png" alt="TranscribeFlow" width={44} height={44} />
        <span className="text-2xl tracking-wide uppercase">
          <span className="font-bold" style={{ color: "#1a365d" }}>Transcribe</span>
          <span className="font-normal" style={{ color: "#2d4a6f" }}>Flow</span>
        </span>
      </Link>
      <div className="flex items-center gap-4">
        {showBack && (
          <Link href="/" className="text-primary hover:underline">
            &larr; Back
          </Link>
        )}
        {showSettings && (
          <Link href="/settings" className="text-primary hover:underline">
            Settings
          </Link>
        )}
      </div>
    </div>
  );
}
