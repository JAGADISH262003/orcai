"use client";

import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

type ToastType = "success" | "error" | "warning" | "info";

interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

interface ToastContextValue {
  toast: (type: ToastType, message: string) => void;
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} });

export const useToast = () => useContext(ToastContext);

let _nextId = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timers = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  const dismiss = useCallback((id: number) => {
    timers.current.delete(id);
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (type: ToastType, message: string) => {
      const id = ++_nextId;
      setToasts((prev) => [...prev.slice(-4), { id, type, message }]);
      const timer = setTimeout(() => dismiss(id), 3000);
      timers.current.set(id, timer);
    },
    [dismiss],
  );

  useEffect(() => {
    return () => {
      timers.current.forEach((t) => clearTimeout(t));
    };
  }, []);

  const ICONS: Record<ToastType, string> = {
    success: "✓",
    error: "✕",
    warning: "⚠",
    info: "ℹ",
  };

  const COLORS: Record<ToastType, string> = {
    success: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    error: "border-red-500/30 bg-red-500/10 text-red-300",
    warning: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    info: "border-[#5e6ad2]/30 bg-[#5e6ad2]/10 text-[#7c87e0]",
  };

  const LIGHT_COLORS: Record<ToastType, string> = {
    success: "border-emerald-500/30 bg-emerald-50 text-emerald-700",
    error: "border-red-500/30 bg-red-50 text-red-700",
    warning: "border-amber-500/30 bg-amber-50 text-amber-700",
    info: "border-[#5e6ad2]/30 bg-[#5e6ad2]/5 text-[#5e6ad2]",
  };

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
        {toasts.map((t) => {
          const isLight = typeof document !== "undefined" && document.documentElement.classList.contains("light");
          return (
            <div
              key={t.id}
              onClick={() => dismiss(t.id)}
              className={`pointer-events-auto cursor-pointer toast-enter px-4 py-2.5 rounded-lg border text-xs font-medium shadow-lg backdrop-blur-sm flex items-center gap-2 max-w-xs ${
                isLight ? LIGHT_COLORS[t.type] : COLORS[t.type]
              }`}
            >
              <span className="text-sm">{ICONS[t.type]}</span>
              <span>{t.message}</span>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
