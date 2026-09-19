import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { API_URL } from "@/lib/server";
import { attachSessionCookies, stripSessionTokens } from "@/lib/session";

export async function POST(request: NextRequest) {
  const body = await request.json();
  try {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) {
      return NextResponse.json({ detail: data.detail ?? "Login failed" }, { status: res.status });
    }
    const { session, refresh_token } = stripSessionTokens(data);
    return attachSessionCookies(NextResponse.json(session), data.access_token as string, refresh_token);
  } catch {
    return NextResponse.json({ detail: "Backend unreachable" }, { status: 502 });
  }
}