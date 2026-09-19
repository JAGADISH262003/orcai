import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { API_URL, TOKEN_COOKIE } from "@/lib/server";

export async function GET(request: NextRequest) {
  const token = request.cookies.get(TOKEN_COOKIE)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }
  try {
    const res = await fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    const data = await res.json();
    if (!res.ok) {
      return NextResponse.json({ detail: data.detail ?? "Invalid session" }, { status: res.status });
    }
    const { access_token, ...session } = data;
    return NextResponse.json(session);
  } catch {
    return NextResponse.json({ detail: "Backend unreachable" }, { status: 502 });
  }
}