import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { API_URL, TOKEN_COOKIE } from "@/lib/server";

// Proxy all /api/* calls (except the auth BFF handlers below) to the FastAPI
// backend, injecting the httpOnly session token server-side.
export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (
    pathname === "/api/auth/login" ||
    pathname === "/api/auth/register" ||
    pathname === "/api/auth/refresh" ||
    pathname === "/api/auth/logout"
  ) {
    return NextResponse.next();
  }

  const token = request.cookies.get(TOKEN_COOKIE)?.value;
  const upstream = new URL(`${API_URL}${pathname.replace("/api", "")}`);
  if (request.nextUrl.search) {
    upstream.search = request.nextUrl.search;
  }

  const headers = new Headers(request.headers);
  headers.set("Origin", request.nextUrl.origin);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const method = request.method;
  const hasBody = !["GET", "HEAD"].includes(method);

  try {
    const upstreamRes = await fetch(upstream.toString(), {
      method,
      headers,
      body: hasBody ? await request.arrayBuffer() : undefined,
      cache: "no-store",
    });

    const response = new NextResponse(upstreamRes.body, {
      status: upstreamRes.status,
      headers: upstreamRes.headers,
    });
    return response;
  } catch (err) {
    console.error("[middleware] upstream fetch failed:", err);
    return NextResponse.json(
      { detail: `Backend unreachable: ${err instanceof Error ? err.message : String(err)}` },
      { status: 502 },
    );
  }
}

export const config = {
  runtime: "nodejs",
  matcher: ["/api/:path*"],
};