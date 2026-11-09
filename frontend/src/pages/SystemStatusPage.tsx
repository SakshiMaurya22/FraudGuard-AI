import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { fetchLiveness, fetchReadiness } from "../api/health";

function StatusRow({ label, state, detail }: { label: string; state: "loading" | "ok" | "error"; detail?: string }) {
  const icon =
    state === "loading" ? <Loader2 className="h-4 w-4 animate-spin text-slate-400" aria-hidden /> :
    state === "ok" ? <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden /> :
    <XCircle className="h-4 w-4 text-red-600" aria-hidden />;
  return (
    <li className="flex items-center gap-3 py-2">
      {icon}
      <span className="font-medium">{label}</span>
      <span className="text-sm text-slate-500">{detail}</span>
    </li>
  );
}

export default function SystemStatusPage() {
  const live = useQuery({ queryKey: ["health", "live"], queryFn: fetchLiveness, retry: false });
  const ready = useQuery({ queryKey: ["health", "ready"], queryFn: fetchReadiness, retry: false });
  const st = (q: { isPending: boolean; isError: boolean }) => (q.isPending ? "loading" : q.isError ? "error" : "ok");

  return (
    <main className="mx-auto max-w-xl p-8">
      <h1 className="text-2xl font-semibold">System status</h1>
      <p className="mt-1 text-sm text-slate-500">Connectivity check between this app and the platform API.</p>
      <ul className="mt-6 divide-y divide-slate-200">
        <StatusRow label="API" state={st(live)} detail={live.isError ? "Cannot reach the API" : undefined} />
        <StatusRow label="Database" state={st(ready)} detail={ready.isError ? "Not ready" : undefined} />
      </ul>
    </main>
  );
}
