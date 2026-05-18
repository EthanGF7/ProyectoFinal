"use client";

import { useEffect, useRef, useState } from "react";

type Status = "launching" | "running" | "error";

export default function AutoLaunchDj({ djId }: { djId: string }) {
  const [status, setStatus] = useState<Status>("launching");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const launchedRef = useRef(false);

  useEffect(() => {
    if (launchedRef.current) return;
    launchedRef.current = true;

    (async () => {
      try {
        const res = await fetch(`/api/djs/${djId}/launch`, { method: "POST" });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          throw new Error(data.error ?? `HTTP ${res.status}`);
        }
        setStatus("running");
      } catch (err) {
        setStatus("error");
        setErrorMsg(err instanceof Error ? err.message : String(err));
      }
    })();
  }, [djId]);

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.6rem",
        padding: "0.6rem 1rem",
        borderRadius: "0.75rem",
        background:
          status === "error"
            ? "rgba(220, 38, 38, 0.15)"
            : status === "running"
            ? "rgba(34, 197, 94, 0.15)"
            : "rgba(168, 85, 247, 0.15)",
        color:
          status === "error"
            ? "#fca5a5"
            : status === "running"
            ? "#86efac"
            : "#d8b4fe",
        fontSize: "0.95rem",
        fontWeight: 500,
      }}
    >
      {status === "launching" && <>⏳ Abriendo visualizador…</>}
      {status === "running" && <>✓ Visualizador abierto</>}
      {status === "error" && <>⚠ Error: {errorMsg}</>}
    </div>
  );
}
