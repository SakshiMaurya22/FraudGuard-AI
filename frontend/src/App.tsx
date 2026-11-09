
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Building2,
  Download,
  Eye,
  FileSearch,
  LayoutDashboard,
  LogOut,
  Menu,
  Network,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  X,
} from "lucide-react";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  getAlerts,
  updateAlertStatus,
  type Alert as ApiAlert,
} from "./api/alerts";
import { apiClient } from "./api/client";

type Page =
  | "Dashboard"
  | "Fraud Alerts"
  | "Banks"
  | "Federated Learning"
  | "Investigations";

type Alert = {
  id: string;
  bank: string;
  account: string;
  amount: number | null;
  score: number;
  severity: string;
  status: string;
  time: string;
};

const trendData = [
  { day: "Mon", detected: 42, prevented: 28 },
  { day: "Tue", detected: 58, prevented: 39 },
  { day: "Wed", detected: 46, prevented: 34 },
  { day: "Thu", detected: 76, prevented: 54 },
  { day: "Fri", detected: 63, prevented: 47 },
  { day: "Sat", detected: 91, prevented: 68 },
  { day: "Sun", detected: 82, prevented: 61 },
];

const bankData = [
  { name: "Alpha", alerts: 128, risk: "High", score: "96.2%" },
  { name: "Beta", alerts: 96, risk: "Medium", score: "94.8%" },
  { name: "Gamma", alerts: 74, risk: "Medium", score: "95.5%" },
];

const navItems: {
  name: Page;
  icon: typeof LayoutDashboard;
}[] = [
  { name: "Dashboard", icon: LayoutDashboard },
  { name: "Fraud Alerts", icon: ShieldAlert },
  { name: "Banks", icon: Building2 },
  { name: "Federated Learning", icon: Network },
  { name: "Investigations", icon: FileSearch },
];

const statuses = [
  "New",
  "Reviewing",
  "Escalated",
  "Resolved",
  "Dismissed",
];


function titleCase(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();
}

function mapAlert(item: ApiAlert): Alert {
  return {
    id: item.id,
    bank: item.bank_reference,
    account: item.pseudonymized_subject_key,
    amount: null,
    score: Math.round(
      item.risk_score <= 1
        ? item.risk_score * 100
        : item.risk_score
    ),
    severity: titleCase(item.severity),
    status: titleCase(item.status),
    time: new Date(item.detected_at).toLocaleString(),
  };
}

function App() {
  const [page, setPage] = useState<Page>("Dashboard");

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [alertsLoading, setAlertsLoading] = useState(true);
  const [alertsError, setAlertsError] = useState("");

  const [statusSaving, setStatusSaving] = useState(false);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Alert | null>(null);
  const [mobileMenu, setMobileMenu] = useState(false);

  const [loginEmail, setLoginEmail] = useState("fraudguard.investigator@example.com");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginBusy, setLoginBusy] = useState(false);
  const [showTokenInput, setShowTokenInput] = useState(false);

  const loadAlerts = async () => {
    setAlertsLoading(true);
    setAlertsError("");

    try {
      const data = await getAlerts();
      const mapped = data.map(mapAlert);

      setAlerts(mapped);

      setSelected((current) =>
        current
          ? mapped.find((a) => a.id === current.id) ?? null
          : null
      );
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Unable to load alerts.";

      if (
        message.includes("401") ||
        message.toLowerCase().includes("unauthorized")
      ) {
        setAlertsError(
          "Authentication required. Connect your investigator access token."
        );
      } else {
        setAlertsError(`Could not load alerts: ${message}`);
      }
    } finally {
      setAlertsLoading(false);
    }
  };

  useEffect(() => {
    void loadAlerts();
  }, []);

  const filteredAlerts = useMemo(() => {
    const query = search.toLowerCase();

    return alerts.filter((a) =>
      `${a.id} ${a.bank} ${a.account} ${a.severity} ${a.status}`
        .toLowerCase()
        .includes(query)
    );
  }, [alerts, search]);

  const updateStatus = async (id: string, status: string) => {
    setStatusSaving(true);
    setAlertsError("");

    try {
      await updateAlertStatus(id, status.toLowerCase());

      setAlerts((old) =>
        old.map((a) =>
          a.id === id ? { ...a, status } : a
        )
      );

      setSelected((current) =>
        current?.id === id
          ? { ...current, status }
          : current
      );
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Status update failed.";

      setAlertsError(`Could not update alert: ${message}`);
    } finally {
      setStatusSaving(false);
    }
  };

  const signIn = async (event: { preventDefault: () => void }) => {
    event.preventDefault();

    const email = loginEmail.trim();

    if (!email || !loginPassword) {
      setAlertsError("Enter your email and password.");
      setShowTokenInput(true);
      return;
    }

    setLoginBusy(true);

    try {
      const response = await apiClient.post<{ access_token: string }>(
        "/auth/login",
        { email, password: loginPassword }
      );

      localStorage.setItem("access_token", response.data.access_token);
      setLoginPassword("");
      setShowTokenInput(false);
      await loadAlerts();
    } catch (error) {
      const status = (error as { response?: { status?: number } }).response
        ?.status;

      setAlertsError(
        status === 401
          ? "Incorrect email or password."
          : "Could not reach the backend. Check that it is running on port 8081."
      );
      setShowTokenInput(true);
    } finally {
      setLoginBusy(false);
    }
  };

  const exportAlerts = () => {
    const headers = [
      "ID",
      "Bank",
      "Pseudonymized Subject",
      "Risk Score",
      "Severity",
      "Status",
      "Detected At",
    ];

    const rows = alerts.map((a) => [
      a.id,
      a.bank,
      a.account,
      a.score,
      a.severity,
      a.status,
      a.time,
    ]);

    const csv = [headers, ...rows]
      .map((row) =>
        row
          .map((value) =>
            `"${String(value).replace(/"/g, '""')}"`
          )
          .join(",")
      )
      .join("\n");

    const blob = new Blob([csv], {
      type: "text/csv;charset=utf-8;",
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = "fraud-alerts.csv";
    link.click();

    URL.revokeObjectURL(url);
  };

  const severityClass = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "critical":
        return "bg-red-500/10 text-red-400 border-red-500/20";
      case "high":
        return "bg-orange-500/10 text-orange-400 border-orange-500/20";
      case "medium":
        return "bg-yellow-500/10 text-yellow-400 border-yellow-500/20";
      default:
        return "bg-blue-500/10 text-blue-400 border-blue-500/20";
    }
  };

  const statusClass = (status: string) => {
    switch (status.toLowerCase()) {
      case "resolved":
        return "bg-emerald-500/10 text-emerald-400";
      case "escalated":
        return "bg-red-500/10 text-red-400";
      case "reviewing":
        return "bg-blue-500/10 text-blue-400";
      case "dismissed":
        return "bg-slate-500/10 text-slate-400";
      default:
        return "bg-yellow-500/10 text-yellow-400";
    }
  };

  const alertTable = (items: Alert[]) => (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-slate-700 text-slate-400">
          <tr>
            <th className="p-3">Alert ID</th>
            <th className="p-3">Bank</th>
            <th className="p-3">Subject</th>
            <th className="p-3">Risk Score</th>
            <th className="p-3">Severity</th>
            <th className="p-3">Status</th>
            <th className="p-3">Detected</th>
            <th className="p-3">Action</th>
          </tr>
        </thead>

        <tbody>
          {items.map((a) => (
            <tr
              key={a.id}
              className="border-b border-slate-800 hover:bg-slate-800/50"
            >
              <td className="p-3 font-mono text-xs text-cyan-400">
                {a.id.slice(0, 12)}
              </td>

              <td className="p-3">{a.bank}</td>

              <td className="p-3 font-mono text-xs">
                {a.account}
              </td>

              <td className="p-3 font-semibold">
                {a.score}%
              </td>

              <td className="p-3">
                <span
                  className={`rounded-full border px-2 py-1 text-xs ${severityClass(a.severity)}`}
                >
                  {a.severity}
                </span>
              </td>

              <td className="p-3">
                <span
                  className={`rounded-full px-2 py-1 text-xs ${statusClass(a.status)}`}
                >
                  {a.status}
                </span>
              </td>

              <td className="p-3 text-xs text-slate-400">
                {a.time}
              </td>

              <td className="p-3">
                <button
                  onClick={() => setSelected(a)}
                  className="rounded-lg p-2 text-cyan-400 hover:bg-slate-700"
                  title="View alert"
                >
                  <Eye size={17} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {items.length === 0 && !alertsLoading && (
        <div className="p-8 text-center text-slate-400">
          No alerts found.
        </div>
      )}
    </div>
  );

  const metricCard = (
    title: string,
    value: string,
    description: string,
    icon: typeof Activity,
    positive = true
  ) => {
    const Icon = icon;

    return (
      <div className="rounded-xl border border-slate-700 bg-slate-900 p-5">
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-400">{title}</p>
          <Icon className="text-cyan-400" size={20} />
        </div>

        <p className="mt-3 text-2xl font-bold">{value}</p>

        <p
          className={`mt-2 flex items-center gap-1 text-xs ${
            positive ? "text-emerald-400" : "text-orange-400"
          }`}
        >
          {positive ? (
            <ArrowUpRight size={14} />
          ) : (
            <ArrowDownRight size={14} />
          )}
          {description}
        </p>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#080f1d] text-slate-100">
      <div className="flex min-h-screen">

        <aside
          className={`fixed inset-y-0 left-0 z-40 w-64 border-r border-slate-800 bg-[#0b1424] p-5 transition-transform lg:static lg:translate-x-0 ${
            mobileMenu ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <div className="mb-10 flex items-center gap-3">
            <div className="rounded-xl bg-cyan-500/10 p-3">
              <Shield className="text-cyan-400" size={25} />
            </div>

            <div>
              <h1 className="text-lg font-bold">FraudGuard AI</h1>
              <p className="text-xs text-slate-400">
                Federated Intelligence
              </p>
            </div>
          </div>

          <p className="mb-3 text-xs uppercase tracking-wider text-slate-500">
            Workspace
          </p>

          <nav className="space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;

              return (
                <button
                  key={item.name}
                  onClick={() => {
                    setPage(item.name);
                    setMobileMenu(false);
                  }}
                  className={`flex w-full items-center gap-3 rounded-lg px-4 py-3 text-sm transition ${
                    page === item.name
                      ? "bg-cyan-500/10 text-cyan-400"
                      : "text-slate-400 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <Icon size={18} />
                  {item.name}
                </button>
              );
            })}
          </nav>

          <div className="mt-10 rounded-xl border border-slate-700 bg-slate-900 p-4">
            <div className="flex items-center gap-2 text-emerald-400">
              <Activity size={16} />
              <span className="text-sm font-medium">
                Platform status
              </span>
            </div>

            <p className="mt-2 text-xs text-slate-400">
              Backend connection is checked when alerts load.
            </p>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-800 bg-[#080f1d]/95 px-5 py-4 backdrop-blur">
            <div className="flex items-center gap-3">
              <button
                className="lg:hidden"
                onClick={() => setMobileMenu(!mobileMenu)}
              >
                <Menu />
              </button>

              <div>
                <h2 className="text-xl font-bold">{page}</h2>
                <p className="text-xs text-slate-400">
                  Federated AI Fraud Detection Platform
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowTokenInput(!showTokenInput)}
                className="rounded-lg border border-slate-700 px-3 py-2 text-xs text-cyan-400 hover:bg-slate-800"
              >
                Connect API
              </button>

              <button
                onClick={() => void loadAlerts()}
                className="rounded-lg border border-slate-700 p-2 hover:bg-slate-800"
                title="Refresh alerts"
              >
                <Activity size={17} />
              </button>

              <button
                onClick={() => {
                  localStorage.removeItem("access_token");
                  setAlerts([]);
                  setSelected(null);
                  setAlertsError("Access token cleared. Connect API again to load alerts.");
                }}
                className="rounded-lg border border-slate-700 p-2 hover:bg-slate-800"
                title="Disconnect API"
              >
                <LogOut size={17} />
              </button>
            </div>
          </header>

          <div className="space-y-6 p-5 lg:p-8">

            {(showTokenInput || alertsError.startsWith("Authentication required")) && (
              <section className="rounded-xl border border-cyan-500/30 bg-slate-900 p-5">
                <h3 className="mb-2 font-semibold">
                  Investigator sign in
                </h3>

                <p className="mb-3 text-xs text-slate-400">
                  Sign in with your investigator account. The session token is
                  stored in this browser's local storage.
                </p>

                <form
                  onSubmit={signIn}
                  className="flex flex-col gap-3 sm:flex-row"
                >
                  <input
                    type="email"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    placeholder="Email"
                    autoComplete="username"
                    className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-sm outline-none focus:border-cyan-500"
                  />

                  <input
                    type="password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="Password"
                    autoComplete="current-password"
                    className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-sm outline-none focus:border-cyan-500"
                  />

                  <button
                    type="submit"
                    disabled={loginBusy}
                    className="rounded-lg bg-cyan-600 px-5 py-3 text-sm font-semibold hover:bg-cyan-500 disabled:opacity-60"
                  >
                    {loginBusy ? "Signing in..." : "Sign in"}
                  </button>
                </form>
              </section>
            )}

            {alertsError && (
              <div className="flex flex-col gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-start gap-2">
                  <AlertTriangle size={18} className="mt-0.5 shrink-0" />
                  <span>{alertsError}</span>
                </div>

                <button
                  onClick={() => setShowTokenInput(true)}
                  className="shrink-0 rounded-lg border border-red-400/30 px-3 py-2 text-xs hover:bg-red-500/10"
                >
                  Connect API
                </button>
              </div>
            )}

            {alertsLoading && (
              <div className="rounded-xl border border-slate-700 bg-slate-900 p-5 text-sm text-slate-400">
                Loading alerts from the backend...
              </div>
            )}

            {page === "Dashboard" && (
              <>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="text-lg font-semibold">
                      Fraud monitoring overview
                    </h3>
                    <p className="text-xs text-slate-400">
                      Live alert counts are taken from the backend.
                    </p>
                  </div>

                  <span className="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-3 py-1 text-xs text-cyan-400">
                    API-connected alerts
                  </span>
                </div>

                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                  {metricCard(
                    "Total alerts",
                    String(alerts.length),
                    "Backend records",
                    ShieldAlert
                  )}

                  {metricCard(
                    "Critical alerts",
                    String(alerts.filter(a => a.severity === "Critical").length),
                    "Backend records",
                    AlertTriangle,
                    false
                  )}

                  {metricCard(
                    "Under review",
                    String(alerts.filter(a => a.status === "Reviewing").length),
                    "Backend records",
                    Eye
                  )}

                  {metricCard(
                    "Resolved",
                    String(alerts.filter(a => a.status === "Resolved").length),
                    "Backend records",
                    ShieldCheck
                  )}
                </div>

                <section className="rounded-xl border border-slate-700 bg-slate-900 p-5">
                  <div className="mb-5 flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold">Recent fraud alerts</h3>
                      <p className="text-xs text-slate-400">
                        Latest records returned by the API
                      </p>
                    </div>

                    <button
                      onClick={() => setPage("Fraud Alerts")}
                      className="text-xs text-cyan-400 hover:underline"
                    >
                      View all
                    </button>
                  </div>

                  {alertTable(alerts.slice(0, 5))}
                </section>

                <section className="rounded-xl border border-slate-700 bg-slate-900 p-5">
                  <div className="mb-3">
                    <h3 className="font-semibold">
                      Illustrative detection trend
                    </h3>
                    <p className="text-xs text-slate-400">
                      Sample chart data, not live backend metrics.
                    </p>
                  </div>

                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={trendData}>
                        <defs>
                          <linearGradient
                            id="detectedGradient"
                            x1="0"
                            y1="0"
                            x2="0"
                            y2="1"
                          >
                            <stop
                              offset="0%"
                              stopColor="#06b6d4"
                              stopOpacity={0.35}
                            />
                            <stop
                              offset="100%"
                              stopColor="#06b6d4"
                              stopOpacity={0}
                            />
                          </linearGradient>
                        </defs>

                        <CartesianGrid
                          strokeDasharray="3 3"
                          stroke="#263449"
                        />

                        <XAxis
                          dataKey="day"
                          stroke="#94a3b8"
                        />

                        <YAxis stroke="#94a3b8" />

                        <Tooltip
                          contentStyle={{
                            background: "#0f172a",
                            border: "1px solid #334155",
                            borderRadius: 8,
                          }}
                        />

                        <Area
                          type="monotone"
                          dataKey="detected"
                          stroke="#06b6d4"
                          fill="url(#detectedGradient)"
                        />

                        <Area
                          type="monotone"
                          dataKey="prevented"
                          stroke="#10b981"
                          fill="transparent"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </section>
              </>
            )}

            {page === "Fraud Alerts" && (
              <section className="rounded-xl border border-slate-700 bg-slate-900 p-5">
                <div className="mb-5 flex flex-col justify-between gap-4 md:flex-row md:items-center">
                  <div>
                    <h3 className="font-semibold">Fraud alert records</h3>
                    <p className="text-xs text-slate-400">
                      {filteredAlerts.length} backend records
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <div className="flex items-center gap-2 rounded-lg border border-slate-700 px-3">
                      <Search size={16} className="text-slate-400" />

                      <input
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder="Search alerts..."
                        className="w-40 bg-transparent py-2 text-sm outline-none"
                      />
                    </div>

                    <button
                      onClick={exportAlerts}
                      className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm hover:bg-slate-800"
                    >
                      <Download size={16} />
                      Export
                    </button>
                  </div>
                </div>

                {alertTable(filteredAlerts)}
              </section>
            )}

            {page === "Banks" && (
              <section className="rounded-xl border border-slate-700 bg-slate-900 p-5">
                <h3 className="mb-2 font-semibold">Participating banks</h3>
                <p className="mb-5 text-xs text-slate-400">
                  Illustrative bank metrics. Connect bank analytics
                  endpoints to replace these sample values.
                </p>

                <div className="grid gap-4 md:grid-cols-3">
                  {bankData.map((bank) => (
                    <div
                      key={bank.name}
                      className="rounded-xl border border-slate-700 p-5"
                    >
                      <Building2 className="mb-3 text-cyan-400" />

                      <h4 className="font-semibold">
                        {bank.name} Bank
                      </h4>

                      <p className="mt-3 text-2xl font-bold">
                        {bank.alerts}
                      </p>

                      <p className="text-xs text-slate-400">
                        Sample alerts
                      </p>

                      <p className="mt-3 text-sm">
                        Model score: {bank.score}
                      </p>

                      <p className="text-xs text-slate-400">
                        Risk: {bank.risk}
                      </p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {page === "Federated Learning" && (
              <section className="rounded-xl border border-slate-700 bg-slate-900 p-6">
                <Network size={35} className="mb-4 text-cyan-400" />

                <h3 className="text-lg font-semibold">
                  Federated learning overview
                </h3>

                <p className="mt-2 text-sm text-slate-400">
                  The platform uses a federated learning architecture
                  so participating banks can train collaboratively
                  without sharing their raw transaction data.
                </p>

                <div className="mt-6 grid gap-4 md:grid-cols-3">
                  {["Alpha Bank", "Beta Bank", "Gamma Bank"].map((bank) => (
                    <div
                      key={bank}
                      className="rounded-xl border border-slate-700 p-5"
                    >
                      <ShieldCheck className="mb-3 text-emerald-400" />
                      <p className="font-semibold">{bank}</p>
                      <p className="mt-2 text-xs text-slate-400">
                        Illustrative participating client
                      </p>
                    </div>
                  ))}
                </div>

                <p className="mt-5 text-xs text-slate-500">
                  Training-round metrics are not connected to a live
                  coordinator endpoint on this screen.
                </p>
              </section>
            )}

            {page === "Investigations" && (
              <section className="rounded-xl border border-slate-700 bg-slate-900 p-6">
                <FileSearch size={35} className="mb-4 text-cyan-400" />

                <h3 className="text-lg font-semibold">
                  Investigation workspace
                </h3>

                <p className="mt-2 text-sm text-slate-400">
                  Select a fraud alert to inspect its pseudonymized
                  subject, risk score, severity, and current status.
                  Investigation case-management features can be
                  connected to the cases API next.
                </p>

                <button
                  onClick={() => setPage("Fraud Alerts")}
                  className="mt-5 rounded-lg bg-cyan-600 px-4 py-2 text-sm font-semibold hover:bg-cyan-500"
                >
                  Open fraud alerts
                </button>
              </section>
            )}

            <footer className="border-t border-slate-800 pt-5 text-center text-xs text-slate-500">
              FraudGuard AI · Academic prototype · Not affiliated
              with JPMorgan Chase.
            </footer>
          </div>
        </main>
      </div>

      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-700 bg-[#0f172a] p-6 shadow-2xl">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold">Alert details</h3>
                <p className="text-xs text-slate-400">
                  Backend alert record
                </p>
              </div>

              <button
                onClick={() => setSelected(null)}
                className="rounded-lg p-2 hover:bg-slate-800"
              >
                <X size={20} />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <p className="text-xs text-slate-500">Alert ID</p>
                <p className="break-all font-mono text-sm">
                  {selected.id}
                </p>
              </div>

              <div>
                <p className="text-xs text-slate-500">Bank reference</p>
                <p className="text-sm">{selected.bank}</p>
              </div>

              <div>
                <p className="text-xs text-slate-500">
                  Pseudonymized subject
                </p>
                <p className="break-all text-sm">{selected.account}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-slate-500">Risk score</p>
                  <p className="text-xl font-bold text-cyan-400">
                    {selected.score}%
                  </p>
                </div>

                <div>
                  <p className="text-xs text-slate-500">Severity</p>
                  <p className="text-sm">{selected.severity}</p>
                </div>
              </div>

              <div>
                <p className="text-xs text-slate-500">Detected at</p>
                <p className="text-sm">{selected.time}</p>
              </div>

              <div className="border-t border-slate-700 pt-4">
                <label className="mb-2 block text-sm font-medium">
                  Update alert status
                </label>

                <select
                  value={selected.status}
                  disabled={statusSaving}
                  onChange={(e) =>
                    void updateStatus(selected.id, e.target.value)
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-sm outline-none focus:border-cyan-500 disabled:opacity-50"
                >
                  {statuses.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>

                {statusSaving && (
                  <p className="mt-2 text-xs text-cyan-400">
                    Saving status to backend...
                  </p>
                )}

                <p className="mt-2 text-xs text-slate-500">
                  Changes are saved through the authenticated API.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
