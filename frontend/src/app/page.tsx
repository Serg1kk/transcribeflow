// app/page.tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { FileUpload } from "@/components/FileUpload";
import { TranscriptionQueue } from "@/components/TranscriptionQueue";

export default function Home() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleUploadComplete = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <main className="container mx-auto py-8 px-4 max-w-4xl">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <Image src="/logo.png" alt="TranscribeFlow" width={40} height={40} />
          <h1 className="text-3xl font-bold">TranscribeFlow</h1>
        </div>
        <Link href="/settings" className="text-primary hover:underline">
          Settings
        </Link>
      </div>

      <div className="space-y-8">
        <FileUpload onUploadComplete={handleUploadComplete} />
        <TranscriptionQueue refreshTrigger={refreshTrigger} />
      </div>
    </main>
  );
}
