export type Env = {
  FAVORITE_API_SECRET: string;
  FAVORITE_ALLOWED_ORIGIN: string;
  PUBLIC_DATA_BASE_URL: string;
  FAVORITES: KVNamespace;
};

export function corsHeaders(env: Env, origin: string | null): HeadersInit {
  const allowed = env.FAVORITE_ALLOWED_ORIGIN;
  return {
    "Access-Control-Allow-Origin": origin && origin === allowed ? origin : allowed,
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Headers": "content-type, authorization",
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
  };
}

export function assertAuthenticated(request: Request, env: Env): void {
  const auth = request.headers.get("authorization") || "";
  const cookie = request.headers.get("cookie") || "";
  const bearer = auth.startsWith("Bearer ") ? auth.slice(7) : "";
  const cookieMatch = cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith("favorite_auth="));
  const cookieSecret = cookieMatch ? decodeURIComponent(cookieMatch.split("=").slice(1).join("=")) : "";
  if (!env.FAVORITE_API_SECRET || (bearer !== env.FAVORITE_API_SECRET && cookieSecret !== env.FAVORITE_API_SECRET)) {
    throw new Error("unauthorized");
  }
}
