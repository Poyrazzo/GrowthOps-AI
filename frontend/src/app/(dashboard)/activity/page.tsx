"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Activity, Search, UserPlus, Brain, FileText, Send, MailOpen,
  CheckCircle2, MessageSquare, Ban,
} from "lucide-react";
import { fetchActivities, ActivityEntry } from "@/lib/api";

// Map each activity_type to an icon + colour so the feed is scannable at a glance.
const TYPE_META: Record<string, { icon: any; color: string; label: string }> = {
  lead_created:            { icon: UserPlus,    color: "text-blue-400",    label: "Lead scraped" },
  lead_enriched:          { icon: Brain,       color: "text-purple-400",  label: "Company enriched" },
  lead_scored:            { icon: Brain,       color: "text-purple-400",  label: "Lead scored" },
  draft_created:          { icon: FileText,    color: "text-amber-400",   label: "Email drafted" },
  email_sent:             { icon: Send,        color: "text-emerald-400", label: "Email sent" },
  reply_received:         { icon: MailOpen,    color: "text-emerald-400", label: "Reply received" },
  reply_classified:       { icon: CheckCircle2,color: "text-emerald-400", label: "Reply classified" },
  linkedin_task_created:  { icon: MessageSquare, color: "text-sky-400",    label: "LinkedIn task" },
  linkedin_task_completed:{ icon: MessageSquare, color: "text-sky-400",    label: "LinkedIn done" },
  lead_magnet_submitted:  { icon: FileText,    color: "text-amber-400",   label: "Form submitted" },
  lead_suppressed:        { icon: Ban,         color: "text-red-400",     label: "Lead suppressed" },
};

function meta(type: string) {
  return TYPE_META[type] || { icon: Activity, color: "text-muted-foreground", label: type.replace(/_/g, " ") };
}

export default function ActivityMonitorPage() {
  // Auto-refresh every 4s so you can literally watch the pipeline work in real time.
  const { data: activities, isLoading, isError } = useQuery({
    queryKey: ["activities-global"],
    queryFn: () => fetchActivities(),
    refetchInterval: 4000,
  });

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
            <Activity className="w-8 h-8 text-primary" />
            Activity Monitor
          </h2>
          <p className="text-muted-foreground mt-1">
            Live feed of everything the system is doing — scraping, scoring, drafting, sending, replies.
            <span className="text-emerald-400"> Auto-refreshing every 4s.</span>
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs font-medium text-emerald-400">Live</span>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="h-16 rounded-xl bg-white/5 animate-pulse border border-white/10" />
          ))}
        </div>
      ) : isError ? (
        <div className="p-8 text-center text-destructive bg-destructive/10 border border-destructive/20 rounded-2xl">
          Failed to load activity feed.
        </div>
      ) : !activities || activities.length === 0 ? (
        <div className="p-16 text-center text-muted-foreground bg-card/40 backdrop-blur-xl border border-white/10 rounded-2xl">
          <Search className="w-12 h-12 mx-auto mb-4 opacity-20" />
          <p className="text-lg font-semibold text-foreground">No activity yet.</p>
          <p className="text-sm mt-2">Activate a campaign or hit "Scrape Now" on a source — events will stream in here.</p>
        </div>
      ) : (
        <div className="relative pl-6">
          {/* vertical timeline rail */}
          <div className="absolute left-2 top-2 bottom-2 w-px bg-white/10" />
          <div className="space-y-3">
            {activities.map((a: ActivityEntry, i) => {
              const m = meta(a.activity_type);
              const Icon = m.icon;
              return (
                <motion.div
                  key={a.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: Math.min(i * 0.02, 0.3) }}
                  className="relative bg-card/40 backdrop-blur-md border border-white/10 rounded-xl p-4 flex items-start gap-4"
                >
                  <div className={`absolute -left-[19px] top-5 w-3 h-3 rounded-full bg-background border-2 ${m.color.replace("text-", "border-")}`} />
                  <div className={`w-9 h-9 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center shrink-0 ${m.color}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-sm font-semibold ${m.color}`}>{m.label}</span>
                      {a.lead_name && (
                        <span className="text-sm text-foreground truncate">· {a.lead_name}</span>
                      )}
                    </div>
                    {a.description && (
                      <p className="text-xs text-muted-foreground mt-1 break-words">{a.description}</p>
                    )}
                  </div>
                  <span className="text-xs text-muted-foreground whitespace-nowrap shrink-0">
                    {new Date(a.created_at).toLocaleTimeString()}
                  </span>
                </motion.div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
