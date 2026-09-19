import { NextRequest, NextResponse } from "next/server";

import { API_URL } from "@/lib/server";
import { clearSessionCookies } from "@/lib/session";

export async function POST(request: NextRequest) {
  const refreshToken = request.cookies.get("orcai_refresh")?.value;
  try {
    if (refreshToken) {
      await fetch(`${API_URL}/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    }
  } catch {
    /* backend unreachable — still clear local session */
  }
  return clearSessionCookies(NextResponse.json({ ok: true }));
}

export async function GET() {
  return POST(new NextRequest("http://localhost/api/auth/logout"));
}