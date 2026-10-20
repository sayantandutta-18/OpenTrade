"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, SessionSummary, StockProfile } from "@/lib/api";
import {
  History,
  Play,
  PlusCircle,
  RefreshCw,
  Search,
  Layers,
} from "lucide-react";

export default function ReplayIndexPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [profiles, setProfiles] = useState<StockProfile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<string>("mid_cap");
  const [seed, setSeed] = useState<number>(42);
  const [warmupSeconds, setWarmupSeconds] = useState<number>(10);
  const [loading, setLoading] = useState<boolean>(true);
  const [creating, setCreating] = useState<boolean>(false);
  const [search, setSearch] = useState<string>("");

  const loadData = async () => {
    setLoading(true);
    try {
      const [sessList, profList] = await Promise.all([
        api.listSessions(50),
        api.getProfiles(),
      ]);
      setSessions(sessList);
      setProfiles(profList);
    } catch (err) {
      console.error("Failed to load sessions:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateAndReplay = async () => {
    setCreating(true);
    try {
      const newSess = await api.createSession(
        selectedProfile,
        Number(seed),
        Number(warmupSeconds)
      );
      router.push(`/replay/${newSess.session_id}`);
    } catch (err) {
      console.error("Failed to create session for replay:", err);
      alert("Failed to create session");
      setCreating(false);
    }
  };

  const filteredSessions = sessions.filter(
    (s) =>
      s.id.toLowerCase().includes(search.toLowerCase()) ||
      s.profile.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Page Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-neutral-800 pb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <History className="w-4 h-4" />
            </div>
            <h1 className="text-2xl font-bold text-neutral-100 tracking-tight">
              Deterministic Event Replay
            </h1>
          </div>
          <p className="text-sm text-neutral-400 mt-1">
            Step through, inspect, and verify order matching from persistent event logs.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="self-start md:self-auto flex items-center gap-2 px-3.5 py-2 text-xs font-medium rounded-lg border border-neutral-800 bg-neutral-900 text-neutral-300 hover:text-neutral-100 hover:bg-neutral-800 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh Sessions
        </button>
      </div>

      {/* Quick Launch Creator */}
      <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2 text-neutral-200 font-semibold text-sm">
          <PlusCircle className="w-4 h-4 text-emerald-400" />
          <span>Launch Fresh Simulation to Replay</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-xs font-mono text-neutral-400 mb-1.5">
              Stock Profile
            </label>
            <select
              value={selectedProfile}
              onChange={(e) => setSelectedProfile(e.target.value)}
              className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-2 text-sm text-neutral-200 focus:outline-none focus:border-emerald-500 font-mono"
            >
              {profiles.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name.replace("_", "-").toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-mono text-neutral-400 mb-1.5">
              Random Seed
            </label>
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
              className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-2 text-sm text-neutral-200 focus:outline-none focus:border-emerald-500 font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-neutral-400 mb-1.5">
              Warm-up (Seconds)
            </label>
            <input
              type="number"
              value={warmupSeconds}
              onChange={(e) => setWarmupSeconds(Number(e.target.value))}
              className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-2 text-sm text-neutral-200 focus:outline-none focus:border-emerald-500 font-mono"
            />
          </div>

          <div>
            <button
              onClick={handleCreateAndReplay}
              disabled={creating}
              className="w-full flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-neutral-950 font-semibold px-4 py-2 rounded-lg text-sm transition-colors disabled:opacity-50"
            >
              <Play className="w-4 h-4 fill-current" />
              {creating ? "Launching..." : "Start & Replay"}
            </button>
          </div>
        </div>
      </div>

      {/* Sessions Table */}
      <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl overflow-hidden space-y-4 p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-neutral-400" />
            <h2 className="font-semibold text-neutral-200 text-sm">
              Saved Simulation Sessions ({sessions.length})
            </h2>
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" />
            <input
              type="text"
              placeholder="Search by ID or profile..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-neutral-950 border border-neutral-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-neutral-200 focus:outline-none focus:border-neutral-700 font-mono"
            />
          </div>
        </div>

        {loading ? (
          <div className="py-12 text-center text-sm text-neutral-500">
            Loading session history...
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="py-12 text-center text-sm text-neutral-500">
            No saved sessions found. Create a session above or run the Simulator to generate events.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-neutral-950/80 text-neutral-400 border-b border-neutral-800">
                <tr>
                  <th className="px-4 py-2.5 font-semibold">Session ID</th>
                  <th className="px-4 py-2.5 font-semibold">Profile</th>
                  <th className="px-4 py-2.5 font-semibold">Seed</th>
                  <th className="px-4 py-2.5 font-semibold">Events Logged</th>
                  <th className="px-4 py-2.5 font-semibold">Created At</th>
                  <th className="px-4 py-2.5 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800/60">
                {filteredSessions.map((s) => (
                  <tr key={s.id} className="hover:bg-neutral-800/40 transition-colors">
                    <td className="px-4 py-3 text-neutral-300 font-medium">
                      {s.id.slice(0, 13)}...
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded bg-neutral-800 border border-neutral-700 text-neutral-200 text-[11px]">
                        {s.profile.replace("_", "-")}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-neutral-400">{s.seed}</td>
                    <td className="px-4 py-3 text-emerald-400 font-bold">
                      {s.event_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-neutral-500">
                      {s.created_at ? new Date(s.created_at).toLocaleTimeString() : "-"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/replay/${s.id}`}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-sans font-medium transition-colors"
                      >
                        <Play className="w-3 h-3 fill-current" />
                        Replay
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
