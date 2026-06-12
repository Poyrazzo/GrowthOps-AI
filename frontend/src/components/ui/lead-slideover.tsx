"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ExternalLink, User, BrainCircuit, MessageSquareText, Trash2, Megaphone, Loader2 } from "lucide-react";
import { Lead, queueLeadDraft } from "@/lib/api";

interface LeadSlideoverProps {
  lead: Lead | null;
  onClose: () => void;
  onDelete?: (lead: Lead) => void;
}

export function LeadSlideover({ lead, onClose, onDelete }: LeadSlideoverProps) {
  const [queueState, setQueueState] = useState<'idle' | 'loading' | 'done' | 'error'>('idle');
  const [queueMessage, setQueueMessage] = useState("");
  const displayName = lead ? `${lead.first_name || ""} ${lead.last_name || ""}`.trim() || "Unnamed Prospect" : "";
  const isScorePending = lead ? !lead.score_reason : false;

  const handleQueue = async () => {
    if (!lead) return;
    setQueueState('loading');
    try {
      const res = await queueLeadDraft(lead.id);
      setQueueState('done');
      setQueueMessage(res.detail);
    } catch (err: unknown) {
      setQueueState('error');
      setQueueMessage(err instanceof Error ? err.message : "Failed to queue drafting.");
    }
  };

  return (
    <AnimatePresence>
      {lead && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
          />
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="fixed inset-y-0 right-0 w-full max-w-md bg-card/90 backdrop-blur-xl border-l border-white/10 shadow-[-10px_0_30px_rgba(0,0,0,0.5)] z-50 flex flex-col"
          >
            <div className="p-6 border-b border-white/10 flex items-start justify-between bg-black/20">
              <div>
                <h2 className="text-2xl font-bold text-foreground">
                  {displayName}
                </h2>
                <p className="text-muted-foreground mt-1 flex items-center gap-2">
                  <User className="w-4 h-4" /> {lead.title || "Unknown Title"}
                </p>
              </div>
              <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full transition-colors text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Score Banner */}
              <div className={`p-4 rounded-xl border flex items-center justify-between ${
                isScorePending ? 'bg-blue-500/10 border-blue-500/20 text-blue-300' :
                lead.lead_score >= 80 ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' :
                lead.lead_score >= 50 ? 'bg-amber-500/10 border-amber-500/20 text-amber-400' :
                'bg-white/5 border-white/10 text-muted-foreground'
              }`}>
                <div>
                  <p className="text-sm uppercase tracking-wider font-semibold opacity-80">Lead Score</p>
                  <p className="text-3xl font-black">
                    {isScorePending ? "Pending" : lead.lead_score}
                    {!isScorePending && <span className="text-lg opacity-50 font-medium">/100</span>}
                  </p>
                </div>
                <BrainCircuit className="w-10 h-10 opacity-50" />
              </div>

              {/* Status & Contact */}
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Contact Info</h3>
                <div className="bg-black/20 rounded-lg p-4 border border-white/5 space-y-2">
                  <p className="text-foreground">{lead.email || "No email available"}</p>
                  {lead.linkedin_url && (
                    <a href={lead.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:text-primary/80 flex items-center gap-2 text-sm transition-colors">
                      View LinkedIn Profile <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                  {lead.profile_url && lead.profile_url !== lead.linkedin_url && (
                    <a href={lead.profile_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:text-primary/80 flex items-center gap-2 text-sm transition-colors">
                      View Source Profile <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>

              {/* Attribution: where this lead came from and which campaign owns it */}
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <Megaphone className="w-4 h-4" /> Attribution
                </h3>
                <div className="bg-black/20 rounded-lg p-4 border border-white/5 space-y-2 text-sm">
                  <div className="flex justify-between gap-2">
                    <span className="text-muted-foreground">Campaign</span>
                    <span className="text-foreground text-right truncate">{lead.campaign_name || "Not assigned"}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-muted-foreground">Company</span>
                    <span className="text-foreground text-right truncate">{lead.company_name || "Unknown"}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-muted-foreground">Scraped from</span>
                    <span className="text-foreground text-right truncate" title={lead.source_url || undefined}>
                      {lead.source_url ? new URL(lead.source_url).hostname : "Manual entry"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Lead intelligence */}
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <BrainCircuit className="w-4 h-4" /> Lead Intelligence Report
                </h3>
                <div className="bg-primary/5 rounded-lg p-4 border border-primary/20 space-y-4">
                  <div>
                    <p className="text-xs text-primary/70 font-semibold mb-1">SCORING LOGIC</p>
                    <p className="text-sm text-foreground/90 leading-relaxed">
                      {lead.score_reason || "Scoring is queued or still running."}
                    </p>
                  </div>
                  <div className="pt-4 border-t border-primary/10">
                    <p className="text-xs text-primary/70 font-semibold mb-1 flex items-center gap-1">
                      <MessageSquareText className="w-3 h-3" /> RECOMMENDED ANGLE
                    </p>
                    <p className="text-sm text-foreground/90 leading-relaxed italic">
                      &quot;{lead.recommended_message_angle || "Generic approach recommended."}&quot;
                    </p>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="p-6 border-t border-white/10 bg-black/20 space-y-3">
              {queueMessage && (
                <p className={`text-xs ${queueState === 'error' ? 'text-destructive' : 'text-emerald-400'}`}>
                  {queueMessage}
                </p>
              )}
              <button
                onClick={handleQueue}
                disabled={lead.status !== 'uncontacted' || queueState === 'loading' || queueState === 'done'}
                className="w-full py-3 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-primary text-primary-foreground hover:bg-primary/90 shadow-[0_0_15px_rgba(var(--primary),0.3)]"
              >
                {queueState === 'loading' && <Loader2 className="w-4 h-4 animate-spin" />}
                {queueState === 'done' ? 'Drafting Queued ✓' :
                 lead.status === 'uncontacted' ? 'Queue for Outreach' : 'Already Processed'}
              </button>
              {onDelete && (
                <button
                  onClick={() => onDelete(lead)}
                  className="w-full py-2.5 rounded-xl font-medium flex items-center justify-center gap-2 transition-all border border-destructive/30 text-destructive hover:bg-destructive/10"
                >
                  <Trash2 className="w-4 h-4" /> Delete Lead
                </button>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
