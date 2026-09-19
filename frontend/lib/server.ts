const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  process.env.BACKEND_API_URL ??
  "http://localhost:8000/api/v1";

const TOKEN_COOKIE = "orcai_token";
const REFRESH_COOKIE = "orcai_refresh";

export { API_URL, TOKEN_COOKIE, REFRESH_COOKIE };