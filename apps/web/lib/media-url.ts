// Signed media URLs issued by the API.
//
// The server builds the URL of its own (local) storage backend from its PUBLIC_API_BASE_URL
// setting. That can name a host this browser cannot reach, for example a LAN address after the
// machine has moved to another network, and then evidence images silently fail to load. A URL
// on the platform's own storage route is the API itself, so it is re-addressed to the API base
// this console already uses. The signature covers the method, bucket, path and expiry, not the
// host, so it stays valid. URLs of external storage (e.g. Supabase) are returned unchanged.

const LOCAL_STORAGE_ROUTE = "/storage/local/";

export function resolveMediaUrl(url: string | null | undefined, apiBaseUrl: string): string | null {
  if (!url) return null;
  try {
    const target = new URL(url);
    if (!target.pathname.includes(LOCAL_STORAGE_ROUTE)) return url;
    const base = new URL(apiBaseUrl);
    target.protocol = base.protocol;
    target.host = base.host;
    return target.toString();
  } catch {
    return url;
  }
}
