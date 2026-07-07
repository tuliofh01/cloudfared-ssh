import { logEvent } from "./logger";

export async function handleFingerprint(req: Request, env: any, start: number) {
  const data = await req.json();
  const hash = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(JSON.stringify(data))
  );

  const fingerprintHash = Array.from(new Uint8Array(hash))
    .map(b => b.toString(16).padStart(2, "0"))
    .join("");

  const userId = fingerprintHash.slice(0, 16);

  await env.DB.prepare(
    "INSERT OR IGNORE INTO users (id, fingerprint_hash, similarity_group, created_at) VALUES (?, ?, ?, ?)"
  )
    .bind(userId, fingerprintHash, fingerprintHash.slice(0, 6), Date.now())
    .run();

  await logEvent(env, {
    event_type: "FINGERPRINT_REGISTERED",
    latency_ms: Date.now() - start,
    req,
    userId
  });

  return Response.json({ userId, fingerprintHash });
}
