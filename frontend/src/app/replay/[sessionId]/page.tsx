"use client";

import { useEffect, useRef, useState, use } from "react";
import Link from "next/link";
import { api, ReplayVerifyResponse } from "@/lib/api";
import { buildReplayFrames, ReplayFrame } from "@/lib/replay";
import { OrderBookLadder } from "@/components/OrderBookLadder";
import { DepthChart } from "@/components/DepthChart";
import { TradeTape } from "@/components/TradeTape";
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Info,
  Pause,
  Play,
  SkipBack,
  SkipForward,
  ShieldCheck,
} from "lucide-react";

export default function ReplayDetailPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const resolvedParams = use(params);
  const sessionId = resolvedParams.sessionId;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [frames, setFrames] = useState<ReplayFrame[]>([]);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(2); // 1x, 2x, 5x, 10x
  const [verifyStatus, setVerifyStatus] = useState<ReplayVerifyResponse | null>(null);
  const [showInspector, setShowInspector] = useState<boolean>(true);

  const playTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Load session events and verification status
  useEffect(() => {
    let mounted = true;
    async function fetchData() {
      try {
        setLoading(true);
        const [events, verify] = await Promise.all([
          api.getEvents(sessionId),
          api.replayVerify(sessionId).catch(() => null),
        ]);

        if (!mounted) return;

        if (events.length === 0) {
          setError("No events found for this session.");
          setLoading(false);
          return;
        }

        setVerifyStatus(verify);

        const computedFrames = buildReplayFrames(events);
        setFrames(computedFrames);
        setCurrentStep(0);
      } catch (err: unknown) {
        if (!mounted) return;
        const msg = err instanceof Error ? err.message : "Failed to load session replay";
        setError(msg);
      } finally {
        if (mounted) setLoading(false);
      }
    }

    fetchData();
    return () => {
      mounted = false;
    };
  }, [sessionId]);

  // Handle Play/Pause playback loop
  useEffect(() => {
    if (isPlaying) {
      const intervalMs = Math.max(20, Math.floor(300 / playbackSpeed));
      playTimerRef.current = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev >= frames.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, intervalMs);
    } else {
      if (playTimerRef.current) {
        clearInterval(playTimerRef.current);
        playTimerRef.current = null;
      }
    }

    return () => {
      if (playTimerRef.current) {
        clearInterval(playTimerRef.current);
      }
    };
  }, [isPlaying, playbackSpeed, frames.length]);

  const currentFrame: ReplayFrame | undefined = frames[currentStep];

  const handleStepForward = (delta = 1) => {
    setIsPlaying(false);
    setCurrentStep((prev) => Math.min(frames.length - 1, prev + delta));
  };

  const handleStepBackward = (delta = 1) => {
    setIsPlaying(false);
    setCurrentStep((prev) => Math.max(0, prev - delta));
  };

  const handleJumpToStart = () => {
    setIsPlaying(false);
    setCurrentStep(0);
  };

  const handleJumpToEnd = () => {
    setIsPlaying(false);
    setCurrentStep(Math.max(0, frames.length - 1));
  };

  // Kind badge styling
  const getKindBadgeClass = (kind: string) => {
    switch (kind) {
      case "ACCEPTED":
        return "bg-sky-500/10 text-sky-400 border-sky-500/30";
      case "TRADE":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "CANCELED":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";
      case "MODIFIED":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      default:
        return "bg-neutral-800 text-neutral-400 border-neutral-700";
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 text-center text-sm font-mono text-neutral-400">
        Reconstructing order book timeline from event log...
      </div>
    );
  }

  if (error || !currentFrame) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 text-center space-y-4">
        <div className="text-rose-400 text-sm font-mono">{error || "No frame data available"}</div>
        <Link
          href="/replay"
          className="inline-flex items-center gap-2 text-xs font-mono text-neutral-400 hover:text-neutral-200"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Replay Sessions
        </Link>
      </div>
    );
  }

  const progressPct =
    frames.length > 1 ? ((currentStep / (frames.length - 1)) * 100).toFixed(1) : "0";

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Breadcrumb & Session Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-neutral-800 pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Link
              href="/replay"
              className="text-neutral-400 hover:text-neutral-200 text-xs font-mono flex items-center gap-1 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Sessions
            </Link>
            <span className="text-neutral-600">/</span>
            <span className="text-xs font-mono text-neutral-400 truncate max-w-xs">
              {sessionId}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-neutral-100 tracking-tight">
              Session Replay
            </h1>
            {verifyStatus && verifyStatus.verified_deterministic && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                <ShieldCheck className="w-3.5 h-3.5" />
                Verified Deterministic
              </span>
            )}
          </div>
        </div>

        {/* Stats Pills */}
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <div className="px-3 py-1.5 rounded-lg bg-neutral-900 border border-neutral-800 text-neutral-300">
            Events: <span className="text-emerald-400 font-bold">{frames.length}</span>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-neutral-900 border border-neutral-800 text-neutral-300">
            Trades: <span className="text-sky-400 font-bold">{currentFrame.trades.length}</span>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-neutral-900 border border-neutral-800 text-neutral-300">
            Spread:{" "}
            <span className="text-neutral-100 font-bold">{currentFrame.spread_formatted}</span>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-neutral-900 border border-neutral-800 text-neutral-300">
            Mid: <span className="text-neutral-100 font-bold">{currentFrame.mid_formatted}</span>
          </div>
        </div>
      </div>

      {/* Replay Controls Card */}
      <div className="bg-neutral-900/80 border border-neutral-800 rounded-xl p-5 space-y-4 shadow-xl">
        {/* Scrubber Range Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-mono">
            <div className="flex items-center gap-2">
              <span className="text-neutral-400">Step:</span>
              <span className="text-emerald-400 font-bold">
                {currentStep + 1} / {frames.length}
              </span>
              <span className="text-neutral-600">({progressPct}%)</span>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-neutral-400">Event:</span>
              <span
                className={`px-2 py-0.5 rounded border text-[11px] font-semibold ${getKindBadgeClass(
                  currentFrame.event.kind
                )}`}
              >
                {currentFrame.event.kind}
              </span>
              <span className="text-neutral-400 font-mono">Seq #{currentFrame.event.seq}</span>
            </div>
          </div>

          <input
            type="range"
            min={0}
            max={frames.length - 1}
            value={currentStep}
            onChange={(e) => {
              setIsPlaying(false);
              setCurrentStep(Number(e.target.value));
            }}
            className="w-full h-2 bg-neutral-950 rounded-lg appearance-none cursor-pointer accent-emerald-500"
          />
        </div>

        {/* Action Buttons & Speed Selection */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
          {/* Playback Step Buttons */}
          <div className="flex items-center gap-1 sm:gap-2">
            <button
              onClick={handleJumpToStart}
              title="Jump to Start"
              className="p-2 rounded-lg bg-neutral-950 hover:bg-neutral-800 border border-neutral-800 text-neutral-300 hover:text-white transition-colors"
            >
              <SkipBack className="w-4 h-4" />
            </button>
            <button
              onClick={() => handleStepBackward(10)}
              title="Step -10"
              className="px-2.5 py-2 rounded-lg bg-neutral-950 hover:bg-neutral-800 border border-neutral-800 text-xs font-mono text-neutral-300 hover:text-white transition-colors"
            >
              -10
            </button>
            <button
              onClick={() => handleStepBackward(1)}
              title="Step -1"
              className="p-2 rounded-lg bg-neutral-950 hover:bg-neutral-800 border border-neutral-800 text-neutral-300 hover:text-white transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className={`flex items-center gap-2 px-5 py-2 rounded-lg font-semibold text-xs transition-colors ${
                isPlaying
                  ? "bg-amber-500 hover:bg-amber-400 text-neutral-950"
                  : "bg-emerald-500 hover:bg-emerald-400 text-neutral-950"
              }`}
            >
              {isPlaying ? (
                <>
                  <Pause className="w-4 h-4 fill-current" /> Pause
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" /> Play
                </>
              )}
            </button>

            <button
              onClick={() => handleStepForward(1)}
              title="Step +1"
              className="p-2 rounded-lg bg-neutral-950 hover:bg-neutral-800 border border-neutral-800 text-neutral-300 hover:text-white transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => handleStepForward(10)}
              title="Step +10"
              className="px-2.5 py-2 rounded-lg bg-neutral-950 hover:bg-neutral-800 border border-neutral-800 text-xs font-mono text-neutral-300 hover:text-white transition-colors"
            >
              +10
            </button>
            <button
              onClick={handleJumpToEnd}
              title="Jump to End"
              className="p-2 rounded-lg bg-neutral-950 hover:bg-neutral-800 border border-neutral-800 text-neutral-300 hover:text-white transition-colors"
            >
              <SkipForward className="w-4 h-4" />
            </button>
          </div>

          {/* Speed Selector & Inspector Toggle */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 bg-neutral-950 p-1 rounded-lg border border-neutral-800 text-xs font-mono">
              {[0.5, 1, 2, 5, 10, 20].map((spd) => (
                <button
                  key={spd}
                  onClick={() => setPlaybackSpeed(spd)}
                  className={`px-2 py-1 rounded transition-colors ${
                    playbackSpeed === spd
                      ? "bg-emerald-500/20 text-emerald-400 font-bold"
                      : "text-neutral-400 hover:text-neutral-200"
                  }`}
                >
                  {spd}x
                </button>
              ))}
            </div>

            <button
              onClick={() => setShowInspector(!showInspector)}
              className={`px-3 py-1.5 rounded-lg border text-xs font-mono transition-colors ${
                showInspector
                  ? "bg-neutral-800 text-neutral-200 border-neutral-700"
                  : "bg-neutral-950 text-neutral-400 border-neutral-800 hover:text-neutral-200"
              }`}
            >
              Inspector
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid: Order Book & Market Depth & Tape */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Order Book Ladder (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <OrderBookLadder
            bids={currentFrame.bids}
            asks={currentFrame.asks}
            spread={currentFrame.spread}
            spreadFormatted={currentFrame.spread_formatted}
            midFormatted={currentFrame.mid_formatted}
          />
        </div>

        {/* Center / Right Column: Depth Chart + Tape (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          <DepthChart
            bids={currentFrame.bids}
            asks={currentFrame.asks}
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Trades Tape */}
            <TradeTape trades={currentFrame.trades} />

            {/* Event Payload Inspector */}
            {showInspector && (
              <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-4 space-y-3 font-mono text-xs">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
                  <div className="flex items-center gap-2">
                    <Info className="w-4 h-4 text-neutral-400" />
                    <span className="font-semibold text-neutral-200">Event Inspector</span>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded border text-[11px] font-semibold ${getKindBadgeClass(
                      currentFrame.event.kind
                    )}`}
                  >
                    {currentFrame.event.kind}
                  </span>
                </div>

                <div className="space-y-1 text-neutral-400">
                  <div className="flex justify-between py-1 border-b border-neutral-800/40">
                    <span>Sequence:</span>
                    <span className="text-neutral-200 font-bold">
                      {currentFrame.event.seq}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-neutral-800/40">
                    <span>Timestamp (us):</span>
                    <span className="text-neutral-200 font-bold">
                      {currentFrame.event.ts.toLocaleString()}
                    </span>
                  </div>
                </div>

                <div>
                  <span className="text-neutral-500 text-[11px] block mb-1">
                    Raw Payload:
                  </span>
                  <pre className="bg-neutral-950 p-3 rounded-lg border border-neutral-800/80 text-[11px] text-emerald-400 overflow-x-auto max-h-48">
                    {JSON.stringify(currentFrame.event.payload, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
