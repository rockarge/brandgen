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
  preview_url: string | null;
  download_url: string | null;
  brand_story: string | null;
  brand_story_preview: string | null;
  user_agent: string | null;
  referrer: string | null;
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
  deviceCounts: { mobile: number; tablet: number; desktop: number; unknown: number };
  referrerCounts: Record<string, number>;
  soloRevenue: number;
  creditRevenue: number;
  totalRevenue: number;
  totalCreditsPurchased: number;
  totalCreditsRemaining: number;
  estimatedCostCents: number;
  profit: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  hasRealTokens?: boolean;
  totalPageViews: number;
  viewsByPath: Record<string, number>;
};

// ─── Helpers ─────────────────────────────────────────────────────────────────
function fmt(dateStr: string) {
  return new Date(dateStr).toLocaleString("tr-TR", {
    day: "2-digit", month: "short", year: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

function shortId(id: string) { return id.slice(0, 8) + "…"; }

function usd(cents: number) {
  return "$" + (cents / 100).toFixed(2);
}

const STATUS_COLOR: Record<string, string> = {
  done: "#4ade80", error: "#f87171", pending: "#facc15", processing: "#60a5fa",
};
const TIER_COLOR: Record<string, string> = {
  solo: "#c9a84c", single: "#c9a84c", free: "#4b5563",
  starter_pack: "#a78bfa", studio_pack: "#38bdf8",
  pro_pack: "#f472b6", agency: "#fb923c",
  starter: "#a78bfa", pro: "#f472b6",
};
const DEVICE_COLOR: Record<string, string> = {
  mobile: "#c9a84c", desktop: "#60a5fa", tablet: "#a78bfa", unknown: "#4b5563",
};
const DEVICE_ICON: Record<string, string> = {
  mobile: "📱", desktop: "🖥️", tablet: "⬜", unknown: "❓",
};

// ─── Mini Bar Chart ──────────────────────────────────────────────────────────
function BarChart({ data, colors }: { data: Record<string, number>; colors?: Record<string, string> }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...entries.map(e => e[1]), 1);
  if (entries.length === 0) {
    return <div style={{ color: "#4b5563", fontSize: 12, padding: "8px 0" }}>Veri yok</div>;
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {entries.map(([label, val]) => {
        const pct = Math.round((val / max) * 100);
        const color = colors?.[label] ?? "#c9a84c";
        return (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 72, fontSize: 11, color: "#9ca3af", textAlign: "right", flexShrink: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {label}
            </div>
            <div style={{ flex: 1, background: "#1a1a1a", borderRadius: 4, height: 18, overflow: "hidden" }}>
              <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 4, transition: "width 0.4s" }} />
            </div>
            <div style={{ fontSize: 11, color: "#e5e7eb", width: 24, textAlign: "right", flexShrink: 0 }}>
              {val}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Job Detail Modal ────────────────────────────────────────────────────────
function JobModal({ job, onClose }: { job: Job; onClose: () => void }) {
  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={styles.modalHeader}>
          <div>
            <span style={{ ...styles.chip, background: STATUS_COLOR[job.status] ?? "#6b7280", color: "#000" }}>
              {job.status}
            </span>
            {" "}
            <span style={{ ...styles.chip, background: TIER_COLOR[job.tier] ?? "#6b7280" }}>
              {job.tier}
            </span>
            {job.paid && <span style={{ ...styles.chip, background: "#14532d", color: "#4ade80", marginLeft: 4 }}>ÖDENDİ</span>}
          </div>
          <button onClick={onClose} style={styles.closeBtn}>✕</button>
        </div>

        {/* Preview image */}
        {job.preview_url && (
          <div style={{ marginBottom: 16, borderRadius: 8, overflow: "hidden", border: "1px solid #222" }}>
            <img src={job.preview_url} alt="Preview" style={{ width: "100%", maxHeight: 200, objectFit: "cover", display: "block" }} />
          </div>
        )}

        {/* Meta */}
        <div style={styles.metaGrid}>
          <MetaRow label="ID" value={<span style={{ fontFamily: "monospace", fontSize: 11 }}>{job.id}</span>} />
          <MetaRow label="Tarih" value={fmt(job.created_at)} />
          <MetaRow label="Model" value={job.ai_model ?? "—"} />
          {job.referrer && <MetaRow label="Kaynak" value={job.referrer} />}
          {job.user_agent && (
            <MetaRow label="Cihaz" value={
              <span style={{ fontSize: 11, wordBreak: "break-all" }}>{job.user_agent.slice(0, 80)}</span>
            } />
          )}
          {job.stripe_session_id && (
            <MetaRow label="Stripe" value={
              <a
                href={`https://dashboard.stripe.com/payments/${job.stripe_session_id}`}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: "#c9a84c", fontSize: 12, fontFamily: "monospace" }}
              >
                {job.stripe_session_id.slice(0, 20)}…
              </a>
            } />
          )}
        </div>

        {/* Prompt */}
        <div style={styles.sectionLabel}>Prompt</div>
        <div style={styles.textBlock}>{job.prompt}</div>

        {/* Brand story preview */}
        {(job.brand_story_preview || job.brand_story) && (
          <>
            <div style={styles.sectionLabel}>Brand Story</div>
            <div style={{ ...styles.textBlock, maxHeight: 180, overflowY: "auto" }}>
              {job.brand_story_preview || job.brand_story?.slice(0, 600)}
            </div>
          </>
        )}

        {/* Error */}
        {job.error && (
          <>
            <div style={{ ...styles.sectionLabel, color: "#f87171" }}>Hata</div>
            <div style={{ ...styles.textBlock, borderColor: "#450a0a", color: "#f87171" }}>{job.error}</div>
          </>
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
          {job.download_url && (
            <a href={job.download_url} target="_blank" rel="noopener noreferrer" style={styles.actionBtn}>
              ⬇ İndir
            </a>
          )}
          {job.preview_url && (
            <a href={job.preview_url} target="_blank" rel="noopener noreferrer" style={{ ...styles.actionBtn, background: "#1a2a1a", color: "#4ade80", border: "1px solid #14532d" }}>
              👁 Preview
            </a>
          )}
          {job.stripe_session_id && (
            <a
              href={`https://dashboard.stripe.com/payments/${job.stripe_session_id}`}
              target="_blank" rel="noopener noreferrer"
              style={{ ...styles.actionBtn, background: "#1a1a2a", color: "#a78bfa", border: "1px solid #312e81" }}
            >
              💳 Stripe
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "flex-start", padding: "4px 0", borderBottom: "1px solid #1a1a1a" }}>
      <div style={{ color: "#6b7280", fontSize: 11, width: 64, flexShrink: 0, paddingTop: 2 }}>{label}</div>
      <div style={{ color: "#d1d5db", fontSize: 13 }}>{value}</div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
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
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

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

  useEffect(() => {
    if (!authed || !secret) return;
    const id = setInterval(() => fetchData(secret), 60_000);
    return () => clearInterval(id);
  }, [authed, secret, fetchData]);

  // Escape key closes modal
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") setSelectedJob(null); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const filteredJobs = jobs.filter(j => {
    if (filter === "paid") return j.paid;
    if (filter === "done") return j.status === "done";
    if (filter === "error") return j.status === "error";
    return true;
  });

  // ── Giriş ekranı ────────────────────────────────────────────────────────────
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
              onChange={e => setSecret(e.target.value)}
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

  // ── Ana panel ───────────────────────────────────────────────────────────────
  return (
    <div style={styles.wrap}>
      {selectedJob && <JobModal job={selectedJob} onClose={() => setSelectedJob(null)} />}

      {/* ── Header ── */}
      <div style={styles.header}>
        <span style={styles.logo}>⚡ BrandGen Admin</span>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {lastRefresh && (
            <span style={styles.refreshLabel}>
              {lastRefresh.toLocaleTimeString("tr-TR")} · otomatik yenileme 60s
            </span>
          )}
          <button onClick={() => fetchData(secret)} disabled={loading} style={styles.btnSmall}>
            {loading ? "…" : "↻ Yenile"}
          </button>
        </div>
      </div>

      {stats && (
        <>
          {/* ── Stat kartları: üst sıra ── */}
          <div style={styles.cardRow}>
            <StatCard label="Toplam İş" value={stats.totalJobs} color="#c9a84c" sub="tüm zamanlar" />
            <StatCard label="Tamamlanan" value={stats.doneJobs} color="#4ade80" sub={`%${stats.totalJobs ? Math.round(stats.doneJobs/stats.totalJobs*100) : 0} başarı`} />
            <StatCard label="Hata" value={stats.errorJobs} color="#f87171" sub="üretim hatası" />
            <StatCard label="Bekleyen" value={stats.pendingJobs} color="#facc15" sub="işlemde" />
            <StatCard label="Ödendi" value={stats.paidJobs} color="#60a5fa" sub="solo job" />
            <StatCard label="Paket Satışı" value={stats.totalCreditsPurchased} color="#a78bfa" sub="credits" />
            <StatCard label="Kalan Hak" value={stats.totalCreditsRemaining} color="#fb923c" sub="bakiye" />
          </div>

          {/* ── Gelir / Gider / Kar kartları ── */}
          <div style={styles.revenueRow}>
            {/* Gelir */}
            <div style={styles.revenueCard}>
              <div style={styles.revenueLabel}>Toplam Gelir</div>
              <div style={styles.revenueValue}>{usd(stats.totalRevenue)}</div>
              <div style={{ display: "flex", gap: 16, marginTop: 8 }}>
                <div>
                  <div style={styles.revenueSub}>{usd(stats.soloRevenue)}</div>
                  <div style={styles.revenueSubLabel}>Solo ödemeler</div>
                </div>
                <div style={{ width: 1, background: "#222" }} />
                <div>
                  <div style={styles.revenueSub}>{usd(stats.creditRevenue)}</div>
                  <div style={styles.revenueSubLabel}>Paket satışları</div>
                </div>
              </div>
            </div>

            {/* Gider (token maliyet) */}
            <div style={{ ...styles.revenueCard, borderLeftColor: "#f87171", borderColor: "#f8717133" }}>
              <div style={styles.revenueLabel}>
                Token Maliyeti {stats.hasRealTokens ? "✓ Gerçek" : "(Tahmini)"}
              </div>
              <div style={{ ...styles.revenueValue, color: "#f87171" }}>{usd(stats.estimatedCostCents)}</div>
              <div style={{ display: "flex", gap: 16, marginTop: 8 }}>
                <div>
                  <div style={{ ...styles.revenueSub, color: "#f87171", fontSize: 13 }}>
                    {(stats.totalInputTokens / 1000).toFixed(0)}K
                  </div>
                  <div style={styles.revenueSubLabel}>input token</div>
                </div>
                <div style={{ width: 1, background: "#222" }} />
                <div>
                  <div style={{ ...styles.revenueSub, color: "#f87171", fontSize: 13 }}>
                    {(stats.totalOutputTokens / 1000).toFixed(0)}K
                  </div>
                  <div style={styles.revenueSubLabel}>output token</div>
                </div>
              </div>
              <div style={{ color: "#4b5563", fontSize: 10, marginTop: 6 }}>
                * Haiku/Sonnet kullanımına göre tahmini
              </div>
            </div>

            {/* Net Kar */}
            <div style={{
              ...styles.revenueCard,
              borderLeftColor: stats.profit >= 0 ? "#4ade80" : "#f87171",
              borderColor: stats.profit >= 0 ? "#4ade8033" : "#f8717133",
            }}>
              <div style={styles.revenueLabel}>Net Kar</div>
              <div style={{
                ...styles.revenueValue,
                color: stats.profit >= 0 ? "#4ade80" : "#f87171",
              }}>
                {stats.profit >= 0 ? "+" : ""}{usd(stats.profit)}
              </div>
              <div style={{ color: "#4b5563", fontSize: 11, marginTop: 8 }}>
                Gelir − Token Gideri
              </div>
              {stats.totalRevenue > 0 && (
                <div style={{ color: "#6b7280", fontSize: 11, marginTop: 4 }}>
                  Margin: %{Math.round((stats.profit / stats.totalRevenue) * 100)}
                </div>
              )}
            </div>

            {/* Cihaz dağılımı */}
            <div style={styles.chartCard}>
              <div style={styles.chartTitle}>Cihaz Dağılımı</div>
              <div style={{ display: "flex", gap: 12, marginBottom: 12, flexWrap: "wrap" }}>
                {Object.entries(stats.deviceCounts).filter(([,v]) => v > 0).map(([k, v]) => (
                  <div key={k} style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 20 }}>{DEVICE_ICON[k]}</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: DEVICE_COLOR[k] }}>{v}</div>
                    <div style={{ fontSize: 10, color: "#6b7280" }}>{k}</div>
                  </div>
                ))}
              </div>
              {stats.totalJobs > 0 && (
                <div style={{ display: "flex", height: 8, borderRadius: 4, overflow: "hidden", gap: 1 }}>
                  {Object.entries(stats.deviceCounts).filter(([,v]) => v > 0).map(([k, v]) => (
                    <div
                      key={k}
                      title={`${k}: ${v}`}
                      style={{
                        flex: v,
                        background: DEVICE_COLOR[k],
                        transition: "flex 0.4s",
                      }}
                    />
                  ))}
                </div>
              )}
              {stats.totalJobs === 0 && <div style={{ color: "#4b5563", fontSize: 12 }}>Veri yok</div>}
            </div>

            {/* Referrer dağılımı */}
            <div style={styles.chartCard}>
              <div style={styles.chartTitle}>Trafik Kaynağı</div>
              <BarChart data={stats.referrerCounts} />
            </div>
          </div>

          {/* Tier dağılımı */}
          <div style={styles.tierRow}>
            {Object.entries(stats.tierCounts).map(([tier, count]) => (
              <span key={tier} style={{ ...styles.tierChip, background: TIER_COLOR[tier] ?? "#4b5563" }}>
                {tier} ({count})
              </span>
            ))}
          </div>

          {/* ── Sayfa görüntülemeleri ── */}
          <div style={styles.revenueRow}>
            <div style={{ ...styles.revenueCard, borderLeftColor: "#38bdf8", borderColor: "#38bdf833" }}>
              <div style={styles.revenueLabel}>Sayfa Görüntülemeleri</div>
              <div style={{ ...styles.revenueValue, color: "#38bdf8" }}>{stats.totalPageViews}</div>
              <div style={{ color: "#4b5563", fontSize: 11, marginTop: 8 }}>toplam sayfa ziyareti</div>
            </div>
            <div style={{ ...styles.chartCard, flex: "1 1 300px" }}>
              <div style={styles.chartTitle}>Sayfa Dağılımı</div>
              {Object.keys(stats.viewsByPath).length > 0 ? (
                <BarChart data={Object.fromEntries(
                  Object.entries(stats.viewsByPath).sort((a,b) => b[1]-a[1]).slice(0,8)
                )} />
              ) : (
                <div style={{ color: "#4b5563", fontSize: 12 }}>
                  Henüz veri yok — tracking aktif, yeni ziyaretler kaydedilecek
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* ── Tab bar ── */}
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
            {(["all", "paid", "done", "error"] as const).map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                style={filter === f ? styles.filterActive : styles.filter}
              >
                {f === "all" ? "Tümü" : f === "paid" ? "Ödendi" : f === "done" ? "Bitti" : "Hata"}
              </button>
            ))}
            <span style={styles.countBadge}>{filteredJobs.length} kayıt</span>
            <span style={{ ...styles.countBadge, marginLeft: 0, color: "#6b7280", fontSize: 11 }}>
              · tıkla → detay
            </span>
          </div>

          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr>
                  {["ID", "Tarih", "Tier", "Durum", "Ödendi", "Cihaz", "Kaynak", "Model", "Prompt"].map(h => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredJobs.map(j => (
                  <tr
                    key={j.id}
                    style={{ ...styles.tr, cursor: "pointer" }}
                    onClick={() => setSelectedJob(j)}
                  >
                    <td style={styles.td}>
                      <span style={styles.mono} title={j.id}>{shortId(j.id)}</span>
                    </td>
                    <td style={styles.td}>{fmt(j.created_at)}</td>
                    <td style={styles.td}>
                      <span style={{ ...styles.chip, background: TIER_COLOR[j.tier] ?? "#4b5563" }}>
                        {j.tier}
                      </span>
                    </td>
                    <td style={styles.td}>
                      <span style={{ ...styles.chip, background: STATUS_COLOR[j.status] ?? "#4b5563", color: "#000" }}>
                        {j.status}
                      </span>
                    </td>
                    <td style={{ ...styles.td, textAlign: "center" }}>
                      {j.paid ? "✅" : <span style={{ color: "#4b5563" }}>—</span>}
                    </td>
                    <td style={styles.td}>
                      {j.user_agent ? (
                        <span title={j.user_agent}>
                          {/ipad|tablet/i.test(j.user_agent) ? "⬜" : /mobile|iphone|android/i.test(j.user_agent) ? "📱" : "🖥️"}
                        </span>
                      ) : <span style={{ color: "#4b5563" }}>—</span>}
                    </td>
                    <td style={{ ...styles.td, maxWidth: 100 }}>
                      {j.referrer ? (
                        <span style={{ ...styles.promptCell, color: "#9ca3af", fontSize: 11 }}>
                          {(() => {
                            try { return new URL(j.referrer).hostname.replace(/^www\./, ""); } catch { return j.referrer.slice(0, 20); }
                          })()}
                        </span>
                      ) : <span style={{ color: "#4b5563", fontSize: 11 }}>direkt</span>}
                    </td>
                    <td style={styles.td}>
                      <span style={styles.mono}>{j.ai_model ?? "—"}</span>
                    </td>
                    <td style={{ ...styles.td, maxWidth: 260 }}>
                      <span title={j.prompt} style={styles.promptCell}>
                        {j.prompt.slice(0, 70)}{j.prompt.length > 70 ? "…" : ""}
                      </span>
                    </td>
                  </tr>
                ))}
                {filteredJobs.length === 0 && (
                  <tr>
                    <td colSpan={9} style={{ ...styles.td, textAlign: "center", color: "#4b5563" }}>
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
                {["Session ID", "E-posta", "Tier", "Ödeme", "Kalan Hak", "Tarih"].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {credits.map(c => {
                const TIER_REVENUE: Record<string, number> = {
                  starter_pack: 3900, studio_pack: 9900, pro_pack: 17900, agency: 8900,
                };
                return (
                  <tr key={c.session_id} style={styles.tr}>
                    <td style={styles.td}>
                      <a
                        href={`https://dashboard.stripe.com/payments/${c.session_id}`}
                        target="_blank" rel="noopener noreferrer"
                        style={{ color: "#c9a84c", fontFamily: "monospace", fontSize: 12 }}
                      >
                        {shortId(c.session_id)}
                      </a>
                    </td>
                    <td style={styles.td}>{c.email ?? "—"}</td>
                    <td style={styles.td}>
                      <span style={{ ...styles.chip, background: TIER_COLOR[c.tier] ?? "#4b5563" }}>
                        {c.tier}
                      </span>
                    </td>
                    <td style={{ ...styles.td, color: "#4ade80", fontWeight: 700 }}>
                      {TIER_REVENUE[c.tier] ? usd(TIER_REVENUE[c.tier]) : "—"}
                    </td>
                    <td style={{ ...styles.td, textAlign: "center", fontWeight: 700, color: "#c9a84c" }}>
                      {c.balance}
                    </td>
                    <td style={styles.td}>{fmt(c.updated_at)}</td>
                  </tr>
                );
              })}
              {credits.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ ...styles.td, textAlign: "center", color: "#4b5563" }}>
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
function StatCard({ label, value, color, sub }: { label: string; value: number; color: string; sub?: string }) {
  return (
    <div style={{ ...styles.card, borderColor: color + "44", borderLeftColor: color, borderLeftWidth: 3 }}>
      <div style={{ color, fontSize: 30, fontWeight: 800, lineHeight: 1 }}>{value}</div>
      <div style={{ color: "#e5e7eb", fontSize: 12, marginTop: 4, fontWeight: 600 }}>{label}</div>
      {sub && <div style={{ color: "#4b5563", fontSize: 10, marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────
const styles: Record<string, React.CSSProperties> = {
  wrap: {
    minHeight: "100vh",
    background: "#0a0a0a",
    color: "#e5e7eb",
    fontFamily: "'Space Grotesk', 'Inter', sans-serif",
    padding: "24px 28px",
    maxWidth: 1400,
    margin: "0 auto",
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
    border: "1px solid #1f1f1f",
    borderRadius: 12,
    padding: "40px 36px",
    width: 320,
    display: "flex",
    flexDirection: "column",
    gap: 20,
  },
  logo: {
    fontSize: 17,
    fontWeight: 700,
    color: "#c9a84c",
    letterSpacing: "0.04em",
  },
  input: {
    background: "#1a1a1a",
    border: "1px solid #2a2a2a",
    borderRadius: 8,
    color: "#e5e7eb",
    padding: "10px 14px",
    fontSize: 14,
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
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
    border: "1px solid #2a2a2a",
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
    borderBottom: "1px solid #1a1a1a",
  },
  refreshLabel: { color: "#4b5563", fontSize: 11 },
  cardRow: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
    marginBottom: 16,
  },
  card: {
    background: "#111",
    border: "1px solid",
    borderRadius: 10,
    padding: "14px 16px",
    minWidth: 100,
    flex: "1 1 100px",
    borderLeftStyle: "solid",
  },
  revenueRow: {
    display: "flex",
    gap: 12,
    marginBottom: 16,
    flexWrap: "wrap",
  },
  revenueCard: {
    background: "#111",
    border: "1px solid #c9a84c44",
    borderLeft: "3px solid #c9a84c",
    borderRadius: 10,
    padding: "16px 20px",
    flex: "0 0 220px",
  },
  revenueLabel: { color: "#6b7280", fontSize: 11, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" },
  revenueValue: { color: "#c9a84c", fontSize: 32, fontWeight: 800, lineHeight: 1.1, marginTop: 4 },
  revenueSub: { color: "#4ade80", fontSize: 16, fontWeight: 700 },
  revenueSubLabel: { color: "#4b5563", fontSize: 10, marginTop: 2 },
  chartCard: {
    background: "#111",
    border: "1px solid #1a1a1a",
    borderRadius: 10,
    padding: "16px 20px",
    flex: "1 1 200px",
    minWidth: 180,
  },
  chartTitle: { color: "#6b7280", fontSize: 11, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 12 },
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
    color: "#fff",
  },
  tabBar: {
    display: "flex",
    gap: 4,
    marginBottom: 14,
    borderBottom: "1px solid #1a1a1a",
  },
  tab: {
    background: "transparent",
    border: "none",
    color: "#4b5563",
    padding: "8px 16px",
    cursor: "pointer",
    fontSize: 14,
    borderBottom: "2px solid transparent",
    fontFamily: "inherit",
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
    fontFamily: "inherit",
  },
  filterRow: {
    display: "flex",
    gap: 8,
    alignItems: "center",
    marginBottom: 12,
    flexWrap: "wrap",
  },
  filter: {
    background: "#1a1a1a",
    border: "1px solid #2a2a2a",
    color: "#6b7280",
    borderRadius: 6,
    padding: "5px 12px",
    fontSize: 12,
    cursor: "pointer",
    fontFamily: "inherit",
  },
  filterActive: {
    background: "#c9a84c18",
    border: "1px solid #c9a84c",
    color: "#c9a84c",
    borderRadius: 6,
    padding: "5px 12px",
    fontSize: 12,
    cursor: "pointer",
    fontWeight: 700,
    fontFamily: "inherit",
  },
  countBadge: { marginLeft: "auto", color: "#4b5563", fontSize: 12 },
  tableWrap: {
    overflowX: "auto",
    background: "#0d0d0d",
    borderRadius: 10,
    border: "1px solid #1a1a1a",
  },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 13 },
  th: {
    padding: "10px 14px",
    textAlign: "left" as const,
    color: "#4b5563",
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: "0.07em",
    textTransform: "uppercase" as const,
    borderBottom: "1px solid #1a1a1a",
    whiteSpace: "nowrap" as const,
  },
  tr: { borderBottom: "1px solid #141414", transition: "background 0.15s" },
  td: { padding: "10px 14px", verticalAlign: "middle" as const, whiteSpace: "nowrap" as const },
  chip: {
    borderRadius: 99,
    padding: "2px 8px",
    fontSize: 11,
    fontWeight: 600,
    color: "#fff",
    display: "inline-block",
  },
  mono: { fontFamily: "monospace", fontSize: 12, color: "#6b7280" },
  promptCell: {
    display: "block",
    whiteSpace: "nowrap" as const,
    overflow: "hidden",
    textOverflow: "ellipsis",
    color: "#d1d5db",
  },

  // Modal
  overlay: {
    position: "fixed" as const,
    inset: 0,
    background: "rgba(0,0,0,0.75)",
    backdropFilter: "blur(4px)",
    zIndex: 1000,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
  },
  modal: {
    background: "#111",
    border: "1px solid #222",
    borderRadius: 14,
    padding: "24px 28px",
    width: "100%",
    maxWidth: 620,
    maxHeight: "90vh",
    overflowY: "auto" as const,
    position: "relative" as const,
  },
  modalHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
  },
  closeBtn: {
    background: "#1a1a1a",
    border: "1px solid #2a2a2a",
    color: "#9ca3af",
    borderRadius: 6,
    width: 28,
    height: 28,
    cursor: "pointer",
    fontSize: 14,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: "inherit",
  },
  metaGrid: { marginBottom: 16 },
  sectionLabel: {
    color: "#4b5563",
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: "0.07em",
    textTransform: "uppercase" as const,
    marginBottom: 6,
    marginTop: 12,
  },
  textBlock: {
    background: "#0d0d0d",
    border: "1px solid #1a1a1a",
    borderRadius: 8,
    padding: "10px 12px",
    fontSize: 13,
    color: "#d1d5db",
    lineHeight: 1.6,
    whiteSpace: "pre-wrap" as const,
    wordBreak: "break-word" as const,
  },
  actionBtn: {
    background: "#1a1a1a",
    border: "1px solid #2a2a2a",
    color: "#c9a84c",
    borderRadius: 8,
    padding: "8px 16px",
    fontSize: 13,
    fontWeight: 600,
    textDecoration: "none",
    display: "inline-block",
    cursor: "pointer",
  },
};
