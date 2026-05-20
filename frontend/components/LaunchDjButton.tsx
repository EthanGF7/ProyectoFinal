"use client";

import { useState } from "react";

type Status = "idle" | "launching" | "running" | "error";

export default function LaunchDjButton({
  djId,
  label = "▶ Abrir visualizador",
}: {
  djId: string;
  label?: string;
}) {
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  async function launch() {
    setStatus("launching");
    setErrorMsg(null);
    try {
      const res = await fetch(`/api/djs/${djId}/launch`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        throw new Error(data.error ?? `HTTP ${res.status}`);
      }
      setStatus("running");
      // Volvemos a "idle" a los 3s para permitir relanzar
      setTimeout(() => setStatus("idle"), 3000);
    } catch (err) {
      setStatus("error");
      setErrorMsg(err instanceof Error ? err.message : String(err));
    }
  }

  const disabled = status === "launching";

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={launch}
        disabled={disabled}
        className="inline-flex items-center justify-center gap-2 rounded-xl bg-fuchsia-600 px-5 py-3 font-semibold text-white shadow-lg shadow-fuchsia-600/30 transition hover:bg-fuchsia-500 focus:outline-none focus:ring-2 focus:ring-fuchsia-400 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {status === "launching" && "Abriendo…"}
        {status === "running" && "✓ Abierto"}
        {(status === "idle" || status === "error") && label}
      </button>

      {status === "error" && errorMsg && (
        <p className="text-sm text-red-400">⚠ {errorMsg}</p>
      )}
    </div>
  );
}
