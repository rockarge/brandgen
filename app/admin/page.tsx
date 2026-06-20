"use client";

import { useEffect, useState, useCallback } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────
type Job = {
  id: string;
  prompt: string;
  status: "pending" | "processing" | "done" | "error";
  paid: boolean;
  tier: string;
  ai_model: string | null;
  stripe_session_id: string | null;
  created_at: string;
  expires_at: string;
  error: string | null;
};

type Credit = {
  session_id: string;
  email: string | null;
  tier: string;
  balance: number;
  updated_at: string;
};

type Stats = {
  totalJobs: number;
  paidJobs: number;
  doneJobs: number;
  errorJobs: number;
  pendingJobs: number;
  tierCounts: Record<string, number>;
  totalCreditsPurchased: number;
  totalCreditsRemaining: number;
};

// ─── Helpers ─────────────────────────────────────────────────────────────────
function fmt(dateStr: string) {
  return new Date(dateStr).toLocaleString("tr-TR", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

function shortId(id: string) {
  return id.slice(0, 8) + "…";
}

const STATUS_COLOR: Record<string, string> = {
  done: "#4ade80",
  error: "#f87171",
  pending: "#facc15",
  processing: "#60a5fa",
};

const TIER_COLOR: Record<string, string> = {
  solo: "#c9a84c",
  single: "#c9a84c",
  starter_pack: "#a78bfa",
  studio_pack: "#38bdf8",
  pro_pack: "#f472b6",
  agency: "#fb923c",
  free: "#6b7280",
};

// ─── Component ───────────────────────────────────────────────────────────────
export default function AdminPage() {
  const [secret, setSecret] = useState("");
  const [authed, setAuthed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [credits, setCredits] = useState<Credit[]>([]);
  const [tab, setTab] = useState<"jobs" | "credits">("jobs");
  const [filter, setFilter] = useState<"all" | "paid" | "done" | "error">("all");
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchData = useCallback(async (sec: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/admin/stats?secret=${encodeURIComponent(sec)}`);
      if (res.status === 401) { setError("Yanlış şifre."); setLoading(false); return; }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setStats(data.stats);
      setJobs(data.jobs);
      setCredits(data.credits);
      setAuthed(true);
      setLastRefresh(new Date());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Bağlantı hatası");
    }
    setLoading(false);
  }, []);

  function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    fetchData(secret);
  }

  // Otomatik yenile — 60 sn
  useEffect(() => {
    if (!authed || !secret) return;
    const id = setInterval(() => fetchData(secret), 60_000);
    return () => clearInterval(id);
  }, [authed, secret, fetchData]);

  const filteredJobs = jobs.filter((j) => {
    if (filter === "paid") return j.paid;
    if (filter === "done") return j.status === "done";
    if (filter === "error") return j.status === "error";
    return true;
  });

  // ── Giriş ekranı ──────────────────────────────────────────────────────────
  if (!authed) {
    return (
      <div style={styles.loginWrap}>
        <div style={styles.loginBox}>
          <div style={styles.logo}>⚡ BrandGen Admin</div>
          <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <input
              type="password"
              placeholder="Admin şifresi"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              style={styles.input}
              autoFocus
            />
            {error && <div style={styles.errorBadge}>{error}</div>}
            <button type="submit" disabled={loading} style={styles.btn}>
              {loading ? "Giriyor…" : "Giriş"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // ── Ana panel ─────────────────────────────────────────────────────────────
  return (
    <div style={styles.wrap}>
      {/* Header */}
      <div style={styles.header}>
        <span style={styles.logo}>⚡ BrandGen Admin</span>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          {lastRefresh && (
            <span style={styles.refreshLabel}>
              Son güncelleme: {lastRefresh.toLocaleTimeString("tr-TR")}
            </span>
          )}
          <button onClick={() => fetchData(secret)} disabled={loading} style={styles.btnSmall}>
            {loading ? "…" : "↻ Yenile"}
          </button>
        </div>
      </div>

      {/* Stat kartları */}
      {stats && (
        <div style={styles.cardRow}>
          <StatCard label="Toplam İş" value={stats.totalJobs} color="#c9a84c" />
          <StatCard label="Ödendi" value={stats.paidJobs} color="#4ade80" />
          <StatCard label="Tamamlanan" value={stats.doneJobs} color="#60a5fa" />
          <StatCard label="Hata" value={stats.errorJobs} color="#f87171" />
          <StatCard label="Bekleyen" value={stats.pendingJobs} color="#facc15" />
          <StatCard label="Paket Satışı" value={stats.totalCreditsPurchased} color="#a78bfa" />
          <StatCard label="Kalan Hak" value={stats.totalCreditsRemaining} color="#fb923c" />
        </div>
      )}

      {/* Tier dağılımı */}
      {stats && (
        <div style={styles.tierRow}>
          {Object.entries(stats.tierCounts).map(([tier, count]) => (
            <span key={tier} style={{ ...styles.tierChip, background: TIER_COLOR[tier] ?? "#6b7280" }}>
              {tier} ({count})
            </span>
          ))}
        </div>
      )}

      {/* Tab bar */}
      <div style={styles.tabBar}>
        <button onClick={() => setTab("jobs")} style={tab === "jobs" ? styles.tabActive : styles.tab}>
          Üretimler ({jobs.length})
        </button>
        <button onClick={() => setTab("credits")} style={tab === "credits" ? styles.tabActive : styles.tab}>
          Krediler / Paketler ({credits.length})
        </button>
      </div>

      {/* ── Jobs tablosu ── */}
      {tab === "jobs" && (
        <>
          <div style={styles.filterRow}>
            {(["all", "paid", "done", "error"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                style={filter === f ? styles.filterActive : styles.filter}
              >
                {f === "all" ? "Tümü" : f === "paid" ? "Ödendi" : f === "done" ? "Bitti" : "Hata"}
              </button>
            ))}
            <span style={styles.countBadge}>{filteredJobs.length} kayıt</span>
          </div>

          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr>
                  {["ID", "Tarih", "Tier", "Durum", "Ödendi", "Model", "Prompt", "Hata"].map((h) => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredJobs.map((j) => (
                  <tr key={j.id} style={styles.tr}>
                    <td style={styles.td}>
                      <span style={styles.mono} title={j.id}>{shortId(j.id)}</span>
                    </td>
                    <td style={styles.td}>{fmt(j.created_at)}</td>
                    <td style={styles.td}>
                      <span style={{ ...styles.chip, background: TIER_COLOR[j.tier] ?? "#6b7280" }}>
                        {j.tier}
                      </span>
                    </td>
                    <td style={styles.td}>
                      <span style={{ ...styles.chip, background: STATUS_COLOR[j.status] ?? "#6b7280", color: "#000" }}>
                        {j.status}
                      </span>
                    </td>
                    <td style={{ ...styles.td, textAlign: "center" }}>
                      {j.paid ? "✅" : "❌"}
                    </td>
                    <td style={styles.td}>
                      <span style={styles.mono}>{j.ai_model ?? "—"}</span>
                    </td>
                    <td style={{ ...styles.td, maxWidth: 260 }}>
                      <span title={j.prompt} style={styles.promptCell}>
                        {j.prompt.slice(0, 80)}{j.prompt.length > 80 ? "…" : ""}
                      </span>
                    </td>
                    <td style={{ ...styles.td, color: "#f87171", maxWidth: 160 }}>
                      {j.error ? (
                        <span title={j.error} style={styles.promptCell}>
                          {j.error.slice(0, 60)}{j.error.length > 60 ? "…" : ""}
                        </span>
                      ) : "—"}
                    </td>
                  </tr>
                ))}
                {filteredJobs.length === 0 && (
                  <tr>
                    <td colSpan={8} style={{ ...styles.td, textAlign: "center", color: "#6b7280" }}>
                      Kayıt yok
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* ── Credits tablosu ── */}
      {tab === "credits" && (
        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr>
                {["Session ID", "E-posta", "Tier", "Kalan Hak", "Tarih"].map((h) => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {credits.map((c) => (
                <tr key={c.session_id} style={styles.tr}>
                  <td style={styles.td}>
                    <span style={styles.mono} title={c.session_id}>{shortId(c.session_id)}</span>
                  </td>
                  <td style={styles.td}>{c.email ?? "—"}</td>
                  <td style={styles.td}>
                    <span style={{ ...styles.chip, background: TIER_COLOR[c.tier] ?? "#6b7280" }}>
                      {c.tier}
                    </span>
                  </td>
                  <td style={{ ...styles.td, textAlign: "center", fontWeight: 700, color: "#c9a84c" }}>
                    {c.balance}
                  </td>
                  <td style={styles.td}>{fmt(c.updated_at)}</td>
                </tr>
              ))}
              {credits.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ ...styles.td, textAlign: "center", color: "#6b7280" }}>
                    Henüz paket satışı yok
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Stat Kartı ──────────────────────────────────────────────────────────────
function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ ...styles.card, borderColor: color }}>
      <div style={{ color, fontSize: 28, fontWeight: 800, lineHeight: 1 }}>{value}</div>
      <div style={{ color: "#9ca3af", fontSize: 11, marginTop: 4 }}>{label}</div>
    </div>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────
const styles: Record<string, React.CSSProperties> = {
  wrap: {
    minHeight: "100vh",
    background: "#0a0a0a",
    color: "#e5e7eb",
    fontFamily: "'Space Grotesk', sans-serif",
    padding: "24px 32px",
  },
  loginWrap: {
    minHeight: "100vh",
    background: "#0a0a0a",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  loginBox: {
    background: "#111",
    border: "1px solid #222",
    borderRadius: 12,
    padding: "40px 36px",
    width: 320,
    display: "flex",
    flexDirection: "column",
    gap: 20,
  },
  logo: {
    fontSize: 18,
    fontWeight: 700,
    color: "#c9a84c",
    letterSpacing: "0.04em",
  },
  input: {
    background: "#1a1a1a",
    border: "1px solid #333",
    borderRadius: 8,
    color: "#e5e7eb",
    padding: "10px 14px",
    fontSize: 14,
    outline: "none",
  },
  btn: {
    background: "#c9a84c",
    color: "#000",
    border: "none",
    borderRadius: 8,
    padding: "10px 0",
    fontWeight: 700,
    fontSize: 14,
    cursor: "pointer",
    letterSpacing: "0.04em",
  },
  btnSmall: {
    background: "#1a1a1a",
    color: "#c9a84c",
    border: "1px solid #333",
    borderRadius: 6,
    padding: "6px 14px",
    fontSize: 13,
    cursor: "pointer",
  },
  errorBadge: {
    background: "#450a0a",
    color: "#f87171",
    borderRadius: 6,
    padding: "6px 10px",
    fontSize: 12,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 24,
    paddingBottom: 16,
    borderBottom: "1px solid #1f1f1f",
  },
  refreshLabel: {
    color: "#6b7280",
    fontSize: 12,
  },
  cardRow: {
    display: "flex",
    gap: 12,
    flexWrap: "wrap",
    marginBottom: 16,
  },
  card: {
    background: "#111",
    border: "1px solid",
    borderRadius: 10,
    padding: "14px 18px",
    minWidth: 110,
  },
  tierRow: {
    display: "flex",
    gap: 8,
    flexWrap: "wrap",
    marginBottom: 20,
  },
  tierChip: {
    borderRadius: 99,
    padding: "3px 12px",
    fontSize: 12,
    fontWeight: 600,
    color: "#000",
  },
  tabBar: {
    display: "flex",
    gap: 4,
    marginBottom: 16,
    borderBottom: "1px solid #1f1f1f",
    paddingBottom: 0,
  },
  tab: {
    background: "transparent",
    border: "none",
    color: "#6b7280",
    padding: "8px 16px",
    cursor: "pointer",
    fontSize: 14,
    borderBottom: "2px solid transparent",
  },
  tabActive: {
    background: "transparent",
    border: "none",
    color: "#c9a84c",
    padding: "8px 16px",
    cursor: "pointer",
    fontSize: 14,
    fontWeight: 700,
    borderBottom: "2px solid #c9a84c",
  },
  filterRow: {
    display: "flex",
    gap: 8,
    alignItems: "center",
    marginBottom: 12,
  },
  filter: {
    background: "#1a1a1a",
    border: "1px solid #2a2a2a",
    color: "#9ca3af",
    borderRadius: 6,
    padding: "5px 12px",
    fontSize: 12,
    cursor: "pointer",
  },
  filterActive: {
    background: "#c9a84c22",
    border: "1px solid #c9a84c",
    color: "#c9a84c",
    borderRadius: 6,
    padding: "5px 12px",
    fontSize: 12,
    cursor: "pointer",
    fontWeight: 700,
  },
  countBadge: {
    marginLeft: "auto",
    color: "#6b7280",
    fontSize: 12,
  },
  tableWrap: {
    overflowX: "auto",
    background: "#111",
    borderRadius: 10,
    border: "1px solid #1f1f1f",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: 13,
  },
  th: {
    padding: "10px 14px",
    textAlign: "left" as const,
    color: "#6b7280",
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: "0.06em",
    textTransform: "uppercase" as const,
    borderBottom: "1px solid #1f1f1f",
    whiteSpace: "nowrap" as const,
  },
  tr: {
    borderBottom: "1px solid #1a1a1a",
  },
  td: {
    padding: "10px 14px",
    verticalAlign: "middle" as const,
    whiteSpace: "nowrap" as const,
  },
  chip: {
    borderRadius: 99,
    padding: "2px 8px",
    fontSize: 11,
    fontWeight: 600,
    color: "#000",
    display: "inline-block",
  },
  mono: {
    fontFamily: "monospace",
    fontSize: 12,
    color: "#9ca3af",
  },
  promptCell: {
    display: "block",
    whiteSpace: "nowrap" as const,
    overflow: "hidden",
    textOverflow: "ellipsis",
    color: "#d1d5db",
  },
};
