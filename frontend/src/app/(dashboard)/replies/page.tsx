"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquareReply, ChevronDown, ChevronUp, Loader2, RefreshCw, ThumbsUp, ThumbsDown, AlertCircle, MailX, HelpCircle, UserX, Bot } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL!;

const CATEGORY_META: Record<string, { label: string; color: string; icon: any }> = {
  interested:       { label: "Interested",       color: "bg-green-500/20 text-green-300 border-green-500/30",  icon: ThumbsUp },
  meeting_request:  { label: "Meeting Request",  color: "bg-blue-500/20 text-blue-300 border-blue-500/30",    icon: MessageSquareReply },
  price_question:   { label: "Price Question",   color: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30", icon: HelpCircle },
  not_interested:   { label: "Not Interested",   color: "bg-red-500/20 text-red-300 border-red-500/30",       icon: ThumbsDown },
  unsubscribe:      { label: "Unsubscribe",      color: "bg-red-700/20 text-red-400 border-red-700/30",       icon: MailX },
  bounce:           { label: "Bounce",           color: "bg-orange-500/20 text-orange-300 border-orange-500/30", icon: AlertCircle },
  wrong_person:     { label: "Wrong Person",     color: "bg-purple-500/20 text-purple-300 border-purple-500/30", icon: UserX },
  other:            { label: "Other",            color: "bg-gray-500/20 text-gray-300 border-gray-500/30",    icon: HelpCircle },
};

const SENTIMENT_COLOR: Record<string, string> = {
  positive: "text-green-400",
  negative: "text-red-400",
  neutral:  "text-gray-400",
};

function stripQuoted(body: string): { main: string; quoted: string } {
  const lines = body.split("\n");
  const cutIdx = lines.findIndex(l =>
    l.startsWith(">") || l.match(/^On .+wrote:/) || l.startsWith("--- Original")
  );
  if (cutIdx === -1) return { main: body.trim(), quoted: "" };
  return {
    main:   lines.slice(0, cutIdx).join("\n").trim(),
    quoted: lines.slice(cutIdx).join("\n").trim(),
  };
}

interface Reply {
  id: string;
  body: string;
  received_at: string;
  category: string | null;
  sentiment: string | null;
  confidence: number | null;
  summary: string | null;
  next_action: string | null;
  lead: string;
  message: string;
}

interface Lead {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  title: string;
  company_name: string;
  campaign_name: string;
  status: string;
}

function ReplyCard({ reply, lead }: { reply: Reply; lead: Lead | null }) {
  const [expanded, setExpanded] = useState(false);
  const { main, quoted } = stripQuoted(reply.body);
  const meta = reply.category ? CATEGORY_META[reply.category] ?? CATEGORY_META.other : null;
  const Icon = meta?.icon ?? Bot;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-card border border-border rounded-xl overflow-hidden"
    >
      {/* Header */}
      <div className="p-5 flex items-start justify-between gap-4">
        <div className="flex items-start gap-4 min-w-0">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center shrink-0 text-white font-bold text-sm">
            {lead ? (lead.first_name?.[0] ?? "?") + (lead.last_name?.[0] ?? "") : "?"}
          </div>
          <div className="min-w-0">
            <div className="font-semibold text-foreground">
              {lead ? `${lead.first_name} ${lead.last_name}` : "Unknown Lead"}
            </div>
            <div className="text-sm text-muted-foreground truncate">
              {lead?.email ?? ""}
              {lead?.company_name ? ` · ${lead.company_name}` : ""}
            </div>
            <div className="text-xs text-muted-foreground mt-0.5">
              {new Date(reply.received_at).toLocaleString()}
              {lead?.campaign_name && (
                <span className="ml-2 px-1.5 py-0.5 rounded bg-white/5 text-muted-foreground">
                  {lead.campaign_name}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Category badge */}
        {meta ? (
          <span className={`shrink-0 flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${meta.color}`}>
            <Icon className="w-3.5 h-3.5" />
            {meta.label}
          </span>
        ) : (
          <span className="shrink-0 flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border bg-gray-500/10 text-gray-400 border-gray-500/20">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            Classifying…
          </span>
        )}
      </div>

      {/* Reply summary bar */}
      {reply.summary && (
        <div className="mx-5 mb-4 p-3 rounded-lg bg-primary/10 border border-primary/20 text-sm">
          <div className="flex items-start gap-2">
            <Bot className="w-4 h-4 text-primary mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <span className="text-foreground">{reply.summary}</span>
              {reply.sentiment && (
                <span className={`ml-2 text-xs font-medium ${SENTIMENT_COLOR[reply.sentiment] ?? ""}`}>
                  ({reply.sentiment}
                  {reply.confidence != null && `, ${Math.round(reply.confidence * 100)}% confidence`})
                </span>
              )}
            </div>
          </div>
          {reply.next_action && (
            <div className="mt-2 text-xs text-primary/80 font-medium flex items-center gap-1.5">
              <span className="text-muted-foreground">Next:</span> {reply.next_action}
            </div>
          )}
        </div>
      )}

      {/* Reply body */}
      <div className="px-5 pb-4">
        <div className="bg-muted/30 rounded-lg p-4 text-sm text-foreground/80 whitespace-pre-wrap font-mono leading-relaxed">
          {main || reply.body}
        </div>

        {quoted && (
          <>
            <button
              onClick={() => setExpanded(v => !v)}
              className="mt-2 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              {expanded ? "Hide" : "Show"} original message
            </button>
            <AnimatePresence>
              {expanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden"
                >
                  <div className="mt-2 bg-muted/20 rounded-lg p-4 text-xs text-muted-foreground whitespace-pre-wrap font-mono leading-relaxed border-l-2 border-muted">
                    {quoted}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}
      </div>
    </motion.div>
  );
}

export default function RepliesPage() {
  const [replies, setReplies] = useState<Reply[]>([]);
  const [leads, setLeads] = useState<Record<string, Lead>>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async (quiet = false) => {
    if (!quiet) setLoading(true);
    else setRefreshing(true);
    try {
      const res = await fetch(`${API}/replies/`);
      const data: Reply[] = await res.json();
      setReplies(data);

      // Fetch lead details for each unique lead ID
      const uniqueLeadIds = [...new Set(data.map(r => r.lead).filter(Boolean))];
      const leadMap: Record<string, Lead> = {};
      await Promise.all(
        uniqueLeadIds.map(async id => {
          try {
            const lr = await fetch(`${API}/leads/${id}/`);
            if (lr.ok) leadMap[id] = await lr.json();
          } catch {}
        })
      );
      setLeads(leadMap);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { load(); }, []);

  const categories = ["interested", "meeting_request", "price_question", "not_interested", "unsubscribe", "bounce", "wrong_person", "other"];
  const grouped = Object.fromEntries(
    categories.map(c => [c, replies.filter(r => r.category === c)])
  );
  const unclassified = replies.filter(r => !r.category);

  const positiveCount = replies.filter(r => r.sentiment === "positive").length;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <MessageSquareReply className="w-6 h-6 text-primary" />
            Reply Inbox
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {replies.length} reply{replies.length !== 1 ? "s" : ""} received
            {positiveCount > 0 && (
              <span className="ml-2 text-green-400 font-medium">{positiveCount} positive</span>
            )}
          </p>
        </div>
        <button
          onClick={() => load(true)}
          disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-card border border-border hover:bg-white/5 transition-colors text-sm"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-muted-foreground">
          <Loader2 className="w-6 h-6 animate-spin mr-2" /> Loading replies…
        </div>
      ) : replies.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <MessageSquareReply className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="text-lg font-medium">No replies yet</p>
          <p className="text-sm mt-1">When prospects reply to your outreach emails, they will appear here.</p>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Positive first */}
          {["interested", "meeting_request", "price_question"].map(cat => {
            const items = grouped[cat];
            if (!items?.length) return null;
            const catMeta = CATEGORY_META[cat];
            return (
              <section key={cat}>
                <h2 className={`text-sm font-semibold uppercase tracking-wider mb-3 flex items-center gap-2 ${catMeta.color.split(" ")[1]}`}>
                  <catMeta.icon className="w-4 h-4" />
                  {catMeta.label} ({items.length})
                </h2>
                <div className="space-y-4">
                  {items.map(r => <ReplyCard key={r.id} reply={r} lead={leads[r.lead] ?? null} />)}
                </div>
              </section>
            );
          })}

          {/* Negative / auto-suppressed */}
          {["not_interested", "unsubscribe", "bounce", "wrong_person", "other"].map(cat => {
            const items = grouped[cat];
            if (!items?.length) return null;
            const catMeta = CATEGORY_META[cat];
            return (
              <section key={cat}>
                <h2 className={`text-sm font-semibold uppercase tracking-wider mb-3 flex items-center gap-2 ${catMeta.color.split(" ")[1]}`}>
                  <catMeta.icon className="w-4 h-4" />
                  {catMeta.label} ({items.length})
                </h2>
                <div className="space-y-4">
                  {items.map(r => <ReplyCard key={r.id} reply={r} lead={leads[r.lead] ?? null} />)}
                </div>
              </section>
            );
          })}

          {/* Unclassified */}
          {unclassified.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold uppercase tracking-wider mb-3 text-muted-foreground">
                Pending Classification ({unclassified.length})
              </h2>
              <div className="space-y-4">
                {unclassified.map(r => <ReplyCard key={r.id} reply={r} lead={leads[r.lead] ?? null} />)}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
