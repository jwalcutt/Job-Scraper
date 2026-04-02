"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Nav from "@/components/Nav";
import { api } from "@/lib/api";

interface ApplicationFunnel {
  applied: number;
  phone_screen: number;
  interview: number;
  offer: number;
  rejected: number;
  withdrawn: number;
}

interface WeeklyScore {
  week: string;
  avg_score: number;
  match_count: number;
}

interface TopItem {
  name: string;
  count: number;
}

interface Analytics {
  application_funnel: ApplicationFunnel;
  weekly_scores: WeeklyScore[];
  top_companies: TopItem[];
  top_titles: TopItem[];
  total_matches: number;
  avg_match_score: number | null;
}

const FUNNEL_STEPS: { key: keyof ApplicationFunnel; label: string; color: string; bg: string }[] = [
  { key: "applied",      label: "Applied",      color: "bg-blue-500",   bg: "bg-blue-50" },
  { key: "phone_screen", label: "Phone screen", color: "bg-purple-500", bg: "bg-purple-50" },
  { key: "interview",    label: "Interview",    color: "bg-yellow-500", bg: "bg-yellow-50" },
  { key: "offer",        label: "Offer",        color: "bg-green-500",  bg: "bg-green-50" },
  { key: "rejected",     label: "Rejected",     color: "bg-red-400",    bg: "bg-red-50" },
  { key: "withdrawn",    label: "Withdrawn",    color: "bg-gray-400",   bg: "bg-gray-50" },
];

export default function AnalyticsPage() {
  const router = useRouter();
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<Analytics>("/analytics/me")
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => router.push("/login"));
  }, [router]);

  const totalApps = data
    ? Object.values(data.application_funnel).reduce((a, b) => a + b, 0)
    : 0;
  const funnelMax = data
    ? Math.max(...Object.values(data.application_funnel), 1)
    : 1;
  const weeklyMax = data
    ? Math.max(...data.weekly_scores.map((w) => w.avg_score), 0.01)
    : 1;

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-3xl px-4 py-8">
        <h1 className="text-2xl font-extrabold tracking-tight text-gray-900 mb-6">Analytics</h1>

        {loading && (
          <div className="text-center py-20 text-gray-400 text-sm">Loading analytics...</div>
        )}

        {!loading && data && (
          <div className="space-y-4">
            {/* Overview cards */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "Total matches", value: String(data.total_matches) },
                { label: "Avg score", value: data.avg_match_score !== null ? `${Math.round(data.avg_match_score * 100)}%` : "\u2014" },
                { label: "Applications", value: String(totalApps) },
              ].map((card, idx) => (
                <div
                  key={card.label}
                  className="rounded-xl bg-white p-5 shadow-card animate-card-enter"
                  style={{ animationDelay: `${idx * 60}ms` }}
                >
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">{card.label}</p>
                  <p className="text-3xl font-extrabold text-gray-900 mt-1 tabular-nums">{card.value}</p>
                </div>
              ))}
            </div>

            {/* Application funnel */}
            <div className="rounded-xl bg-white p-5 shadow-card animate-fade-in">
              <h2 className="text-sm font-bold text-gray-900 mb-4">Application funnel</h2>
              {totalApps === 0 ? (
                <p className="text-xs text-gray-400 py-4 text-center">
                  No applications yet.{" "}
                  <Link href="/jobs" className="text-brand-600 hover:underline">Find jobs</Link>
                </p>
              ) : (
                <div className="space-y-2.5">
                  {FUNNEL_STEPS.map(({ key, label, color, bg }) => {
                    const count = data.application_funnel[key];
                    const pct = (count / funnelMax) * 100;
                    return (
                      <div key={key} className="flex items-center gap-3">
                        <span className="w-24 text-xs text-gray-500 text-right shrink-0">{label}</span>
                        <div className={`flex-1 h-6 rounded-lg ${bg} overflow-hidden`}>
                          <div
                            className={`h-full rounded-lg ${color} transition-all duration-700`}
                            style={{ width: `${pct}%`, minWidth: count > 0 ? "2px" : "0" }}
                          />
                        </div>
                        <span className="w-8 text-xs font-bold text-gray-700 tabular-nums">{count}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Weekly match score trend */}
            <div className="rounded-xl bg-white p-5 shadow-card animate-fade-in">
              <h2 className="text-sm font-bold text-gray-900 mb-4">Match score trend</h2>
              {data.weekly_scores.length === 0 ? (
                <p className="text-xs text-gray-400 py-4 text-center">No match data yet.</p>
              ) : (
                <div className="flex items-end gap-1" style={{ height: "120px" }}>
                  {data.weekly_scores.map((w) => {
                    const pct = (w.avg_score / weeklyMax) * 100;
                    const scorePct = Math.round(w.avg_score * 100);
                    const weekLabel = new Date(w.week + "T00:00:00").toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                    });
                    return (
                      <div
                        key={w.week}
                        className="flex-1 flex flex-col items-center justify-end h-full group"
                      >
                        <div className="relative w-full flex justify-center">
                          <span className="absolute -top-5 text-[10px] font-bold text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity tabular-nums">
                            {scorePct}%
                          </span>
                          <div
                            className="w-full max-w-8 rounded-t-lg bg-brand-500 hover:bg-brand-600 transition-all duration-500"
                            style={{ height: `${Math.max(pct, 2)}%` }}
                          />
                        </div>
                        <span className="text-[9px] text-gray-400 mt-1.5 truncate w-full text-center">
                          {weekLabel}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Top companies + Top titles */}
            <div className="grid grid-cols-2 gap-3">
              <RankedList title="Top companies" items={data.top_companies} color="bg-brand-500" />
              <RankedList title="Top titles" items={data.top_titles} color="bg-emerald-500" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function RankedList({
  title,
  items,
  color,
}: {
  title: string;
  items: TopItem[];
  color: string;
}) {
  const max = Math.max(...items.map((i) => i.count), 1);

  return (
    <div className="rounded-xl bg-white p-5 shadow-card">
      <h2 className="text-sm font-bold text-gray-900 mb-3">{title}</h2>
      {items.length === 0 ? (
        <p className="text-xs text-gray-400 py-3 text-center">No data yet.</p>
      ) : (
        <div className="space-y-2.5">
          {items.slice(0, 8).map((item, i) => (
            <div key={item.name} className="flex items-center gap-2">
              <span className="w-4 text-[10px] text-gray-300 text-right shrink-0 tabular-nums font-bold">
                {i + 1}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-xs text-gray-700 truncate font-medium">{item.name}</span>
                  <span className="text-[10px] text-gray-400 shrink-0 ml-2 tabular-nums font-bold">{item.count}</span>
                </div>
                <div className="h-1 rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${color} transition-all duration-700`}
                    style={{ width: `${(item.count / max) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
