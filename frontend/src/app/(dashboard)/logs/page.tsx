"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Terminal, RefreshCw, Filter, Trash2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:18000/api/crm";

const LINE_COLORS: [string, string][] = [
  ["ERROR", "text-red-400"],
  ["WARNING", "text-yellow-400"],
  ["LEAD CREATED", "text-green-400"],
  ["SCRAPE SUCCESS", "text-emerald-400"],
  ["TASK", "text-blue-400"],
  ["DEBUG", "text-gray-500"],
];

function colorLine(line: string): string {
  for (const [kw, cls] of LINE_COLORS) {
    if (line.includes(kw)) return cls;
  }
  return "text-gray-300";
}

export default function LogsPage() {
  const [lines, setLines] = useState<string[]>([]);
  const [filter, setFilter] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastFetch, setLastFetch] = useState<string>("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const fetchLogs = useCallback(async () => {
    try {
      const params = new URLSearchParams({ lines: "300" });
      if (filter) params.set("filter", filter);
      const res = await fetch(`${API_BASE}/logs/?${params}`);
      const data = await res.json();
      setLines(data.lines ?? []);
      setLastFetch(new Date().toLocaleTimeString());
    } catch {
      setLines(["[ERROR] Could not reach the log endpoint. Is Django running?"]);
    }
  }, [filter]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(fetchLogs, 4000);
    return () => clearInterval(id);
  }, [autoRefresh, fetchLogs]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  return (
    <div className="max-w-7xl mx-auto space-y-4 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Terminal className="w-7 h-7 text-primary" />
          <div>
            <h2 className="text-2xl font-bold text-foreground">System Logs</h2>
            <p className="text-xs text-muted-foreground">
              Live view of <code className="text-primary">backend/logs/growthops.log</code>
              {lastFetch && <span className="ml-2">— last updated {lastFetch}</span>}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <Filter className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Filter lines…"
              value={filter}
              onChange={e => setFilter(e.target.value)}
              className="bg-card/40 border border-white/10 rounded-lg py-1.5 pl-9 pr-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 w-48"
            />
          </div>

          <button
            onClick={fetchLogs}
            className="p-2 rounded-lg bg-card/40 border border-white/10 text-muted-foreground hover:text-foreground transition"
            title="Refresh now"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <button
            onClick={() => setAutoRefresh(v => !v)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
              autoRefresh
                ? "bg-green-500/20 border-green-500/40 text-green-400"
                : "bg-card/40 border-white/10 text-muted-foreground"
            }`}
          >
            {autoRefresh ? "Auto-refresh ON" : "Auto-refresh OFF"}
          </button>

          <button
            onClick={() => setLines([])}
            className="p-2 rounded-lg bg-card/40 border border-white/10 text-muted-foreground hover:text-red-400 transition"
            title="Clear display (does not delete the file)"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 bg-black/60 border border-white/10 rounded-xl p-4 overflow-y-auto font-mono text-xs leading-relaxed min-h-[60vh] max-h-[75vh]">
        {lines.length === 0 ? (
          <p className="text-muted-foreground">
            No log lines yet. Click &quot;Run Now&quot; on a campaign or &quot;Scrape Now&quot; on a source, then watch here.
          </p>
        ) : (
          lines.map((line, i) => (
            <div key={i} className={`whitespace-pre-wrap break-all ${colorLine(line)}`}>
              {line}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
