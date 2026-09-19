"use client";

import React from "react";

export function Modal({
  open,
  title,
  onClose,
  children,
  wide = false,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  wide?: boolean;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div
        className={`linear-card bg-[#0f1011] w-full ${wide ? "max-w-3xl" : "max-w-xl"} p-6 space-y-4 border border-white/10 shadow-2xl max-h-[90vh] overflow-y-auto`}
      >
        <div className="flex justify-between items-center">
          <h3 className="text-base font-semibold text-[#f7f8f8]">{title}</h3>
          <button onClick={onClose} className="text-[#8a8f98] hover:text-white" aria-label="Close">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-16 text-xs text-[#8a8f98] space-x-2">
      <span className="w-3 h-3 rounded-full border-2 border-[#5e6ad2] border-t-transparent animate-spin" />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({ text, action }: { text: string; action?: React.ReactNode }) {
  return (
    <div className="linear-card p-10 text-center text-xs text-[#8a8f98] space-y-3">
      <div>{text}</div>
      {action}
    </div>
  );
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-center justify-between p-3 rounded bg-red-500/10 border border-red-500/20 text-xs text-red-300">
      <span>{message}</span>
      {onRetry ? (
        <button onClick={onRetry} className="underline hover:text-red-200">
          Retry
        </button>
      ) : null}
    </div>
  );
}