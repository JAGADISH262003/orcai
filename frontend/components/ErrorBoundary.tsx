"use client";
import React from "react";

interface Props { children: React.ReactNode; fallback?: React.ReactNode; }
interface State { hasError: boolean; error: Error | null; }

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="p-6 bg-[#161618] border border-red-500/20 rounded-lg">
          <h3 className="text-red-400 font-semibold mb-2">Something went wrong</h3>
          <p className="text-[#8a8f98] text-sm">{this.state.error?.message}</p>
          <button onClick={() => this.setState({ hasError: false, error: null })} className="mt-3 text-xs text-brand hover:underline">Try again</button>
        </div>
      );
    }
    return this.props.children;
  }
}
