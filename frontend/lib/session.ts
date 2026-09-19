import { NextResponse } from "next/server";

import { REFRESH_COOKIE, TOKEN_COOKIE } from "@/lib/server";

export function attachSessionCookies(
  response: NextResponse,
  accessToken: string,
  refreshToken?: string | null,
) {
  response.cookies.set(TOKEN_COOKIE, accessToken, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
    secure: process.env.NODE_ENV === "production",
  });
  if (refreshToken) {
    response.cookies.set(REFRESH_COOKIE, refreshToken, {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24 * 30,
      secure: process.env.NODE_ENV === "production",
    });
  }
  return response;
}

export function clearSessionCookies(response: NextResponse) {
  response.cookies.set(TOKEN_COOKIE, "", { path: "/", maxAge: 0 });
  response.cookies.set(REFRESH_COOKIE, "", { path: "/", maxAge: 0 });
  return response;
}

export function stripSessionTokens(data: Record<string, unknown>) {
  const { access_token, refresh_token, ...session } = data;
  return { session, refresh_token: refresh_token as string | undefined };
}