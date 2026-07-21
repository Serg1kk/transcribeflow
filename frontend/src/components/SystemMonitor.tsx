'use client';

// Default no-op implementation of the optional system-monitoring widget.
//
// This file MUST exist for the build to succeed: SystemMonitorWrapper calls
// `import('./SystemMonitor')`, and webpack resolves dynamic imports at compile
// time — a missing module is a hard build error, not something the wrapper's
// `.catch()` can recover from at runtime.
//
// The widget is opt-in via NEXT_PUBLIC_ENABLE_SYSTEM_MONITOR=true. To use a real
// monitor, replace this file locally and keep git from tracking your version:
//   git update-index --skip-worktree frontend/src/components/SystemMonitor.tsx

export function SystemMonitor() {
  return null;
}
