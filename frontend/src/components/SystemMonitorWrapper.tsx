'use client';

import { useEffect, useState, ComponentType } from 'react';

// Only load SystemMonitor if NEXT_PUBLIC_ENABLE_SYSTEM_MONITOR is set
// This allows the project to work without the monitoring widget

export function SystemMonitorWrapper() {
  const [Monitor, setMonitor] = useState<ComponentType | null>(null);
  
  useEffect(() => {
    // Check if system monitoring is enabled via env variable
    const isEnabled = process.env.NEXT_PUBLIC_ENABLE_SYSTEM_MONITOR === 'true';
    
    if (isEnabled) {
      // Dynamically import only if enabled
      import('./SystemMonitor')
        .then(mod => {
          setMonitor(() => mod.SystemMonitor);
        })
        .catch(() => {
          // SystemMonitor.tsx doesn't exist - that's fine
          console.log('SystemMonitor not available (local-only feature)');
        });
    }
  }, []);

  if (!Monitor) return null;
  
  return <Monitor />;
}
