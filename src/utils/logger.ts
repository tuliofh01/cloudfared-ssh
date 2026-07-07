export async function logEvent(
  env: any,
  { event_type, latency_ms, req, userId = "unknown" }: any
) {
  const ip = req.headers.get("CF-Connecting-IP") || "unknown";
  const country = req.headers.get("CF-IPCountry") || "unknown";
  const ua = req.headers.get("User-Agent") || "unknown";

  await env.DB.prepare(`
    INSERT INTO logs
    (user_id, event_type, latency_ms, server_status, ip, country, user_agent, details, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `)
    .bind(
      userId,
      event_type,
      latency_ms,
      "UNKNOWN",
      ip,
      country,
      ua,
      JSON.stringify({ url: req.url }),
      Date.now()
    )
    .run();
}
