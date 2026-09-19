import { NextRequest, NextResponse } from "next/server";

import { API_URL } from "@/lib/server";
import { attachSessionCookies, stripSessionTokens } from "@/lib/session";

export async function POST(request: NextRequest) {
  const refreshToken = request.cookies.get("orcai_refresh")?.value;
  if (!refreshToken) {
    return NextResponse.json({ detail: "Missing refresh token" }, { status: 401 });
  }
  try {
    const res = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    const data = await res.json();
    if (!res.ok) {
      return NextResponse.json({ detail: data.detail ?? "Session expired" }, { status: res.status });
    }
    const { session, refresh_token } = stripSessionTokens(data);
    return attachSessionCookies(NextResponse.json(session), data.access_token as string, refresh_token);
  } catch {
    return NextResponse.json({ detail: "Backend unreachable" }, { status: 502 });
  }
}

export async function GET() {
  return POST(new NextRequest("http://localhost/api/auth/refresh"));
}