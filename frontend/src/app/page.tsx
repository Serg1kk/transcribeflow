// app/page.tsx
"use client";

import { useState } from "react";
import { FileUpload } from "@/components/FileUpload";
import { TranscriptionQueue } from "@/components/TranscriptionQueue";
import { Header } from "@/components/Header";

export default function Home() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleUploadComplete = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <main className="container mx-auto py-8 px-4 max-w-4xl">
      <Header />

      <div className="space-y-8">
        <FileUpload onUploadComplete={handleUploadComplete} />
        <TranscriptionQueue refreshTrigger={refreshTrigger} />
      </div>
    </main>
  );
}
