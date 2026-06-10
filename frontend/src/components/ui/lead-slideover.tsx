"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, ExternalLink, User, BrainCircuit, MessageSquareText } from "lucide-react";
import { Lead } from "@/lib/api";

interface LeadSlideoverProps {
  lead: Lead | null;
  onClose: () => void;
}

export function LeadSlideover({ lead, onClose }: LeadSlideoverProps) {
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
                  {lead.first_name} {lead.last_name}
                </h2>
                <p className="text-muted-foreground mt-1 flex items-center gap-2">
                  <User className="w-4 h-4" /> {lead.title}
                </p>
              </div>
              <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full transition-colors text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Score Banner */}
              <div className={`p-4 rounded-xl border flex items-center justify-between ${
                lead.lead_score >= 80 ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' :
                lead.lead_score >= 50 ? 'bg-amber-500/10 border-amber-500/20 text-amber-400' :
                'bg-white/5 border-white/10 text-muted-foreground'
              }`}>
                <div>
                  <p className="text-sm uppercase tracking-wider font-semibold opacity-80">AI Lead Score</p>
                  <p className="text-3xl font-black">{lead.lead_score}<span className="text-lg opacity-50 font-medium">/100</span></p>
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
                </div>
              </div>

              {/* AI Intelligence */}
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <BrainCircuit className="w-4 h-4" /> AI Intelligence Report
                </h3>
                <div className="bg-primary/5 rounded-lg p-4 border border-primary/20 space-y-4">
                  <div>
                    <p className="text-xs text-primary/70 font-semibold mb-1">SCORING LOGIC</p>
                    <p className="text-sm text-foreground/90 leading-relaxed">
                      {lead.score_reason || "No reasoning provided by AI."}
                    </p>
                  </div>
                  <div className="pt-4 border-t border-primary/10">
                    <p className="text-xs text-primary/70 font-semibold mb-1 flex items-center gap-1">
                      <MessageSquareText className="w-3 h-3" /> RECOMMENDED ANGLE
                    </p>
                    <p className="text-sm text-foreground/90 leading-relaxed italic">
                      "{lead.recommended_message_angle || "Generic approach recommended."}"
                    </p>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="p-6 border-t border-white/10 bg-black/20">
              <button 
                disabled={lead.status !== 'uncontacted'}
                className="w-full py-3 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-primary text-primary-foreground hover:bg-primary/90 shadow-[0_0_15px_rgba(var(--primary),0.3)]"
              >
                {lead.status === 'uncontacted' ? 'Queue for Outreach' : 'Already Processed'}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
