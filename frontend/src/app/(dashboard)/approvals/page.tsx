"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, Variants } from "framer-motion";
import { ShieldCheck, XCircle, CheckCircle2, ShieldAlert, FileText, CheckSquare } from "lucide-react";
import { fetchApprovals, updateApprovalStatus, ApprovalItem } from "@/lib/api";

export default function ApprovalsPage() {
  const queryClient = useQueryClient();

  const { data: approvals, isLoading, isError } = useQuery({
    queryKey: ["approvals"],
    queryFn: fetchApprovals,
  });

  const mutation = useMutation({
    mutationFn: ({ id, status }: { id: string, status: 'approved' | 'rejected' }) => updateApprovalStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
    },
  });

  const pendingApprovals = approvals?.filter(a => a.status === 'pending') || [];

  const container: Variants = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const item: Variants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
          <ShieldCheck className="w-8 h-8 text-primary" />
          Approval Queue
        </h2>
        <p className="text-muted-foreground mt-1">Audit and authorize AI-generated actions before they are executed.</p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-64 rounded-2xl bg-white/5 animate-pulse border border-white/10" />
          ))}
        </div>
      ) : isError ? (
        <div className="p-8 bg-destructive/10 border border-destructive/20 rounded-2xl text-center text-destructive flex flex-col items-center">
          <ShieldAlert className="w-12 h-12 mb-3 opacity-80" />
          <p className="text-lg font-medium">Failed to load Approval Queue.</p>
        </div>
      ) : pendingApprovals.length === 0 ? (
        <div className="p-16 text-center text-muted-foreground bg-card/40 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl">
          <CheckSquare className="w-16 h-16 mx-auto mb-4 opacity-20 text-emerald-500" />
          <p className="text-xl font-semibold text-foreground">Queue is clear.</p>
          <p className="text-sm mt-2">No pending AI actions require your review.</p>
        </div>
      ) : (
        <motion.div 
          variants={container}
          initial="hidden"
          animate="show"
          className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"
        >
          {pendingApprovals.map((approval) => (
            <motion.div 
              key={approval.id}
              variants={item}
              className="bg-card/40 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col group relative"
            >
              {/* Top gradient line */}
              <div className="h-1 w-full bg-gradient-to-r from-primary to-purple-500" />
              
              <div className="p-6 flex-1 flex flex-col">
                <div className="flex items-center justify-between mb-4">
                  <span className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                    <FileText className="w-3 h-3" />
                    {approval.item_type.replace('_', ' ')}
                  </span>
                  <span className="text-xs text-muted-foreground font-mono">
                    {new Date(approval.created_at).toLocaleDateString()}
                  </span>
                </div>

                <div className="mb-4">
                  <h3 className="text-sm font-semibold text-primary/80 mb-2 uppercase tracking-wider">Reason For Review</h3>
                  <p className="text-foreground/90 text-sm leading-relaxed">
                    {approval.reason_for_review || "No specific reason provided. General audit required."}
                  </p>
                </div>

                {approval.context_data ? (
                  <div className="space-y-3 mb-6 flex-1">
                    {/* Lead context (SRS 3.15) */}
                    <div className="p-4 bg-black/30 rounded-xl border border-white/5">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider font-semibold">Lead</p>
                      <p className="text-sm text-foreground font-medium">
                        {approval.context_data.lead_name}
                        {approval.context_data.lead_title && <span className="text-muted-foreground"> — {approval.context_data.lead_title}</span>}
                      </p>
                      <p className="text-xs text-muted-foreground">{approval.context_data.lead_email}</p>
                      <p className="text-xs mt-1">
                        <span className="text-primary font-semibold">Score {approval.context_data.lead_score}/100</span>
                        {approval.context_data.score_reason && (
                          <span className="text-muted-foreground"> · {approval.context_data.score_reason}</span>
                        )}
                      </p>
                    </div>

                    {/* Proposed action: the actual draft, or the AI's reply analysis */}
                    {approval.context_data.kind === 'message_draft' ? (
                      <div className="p-4 bg-black/30 rounded-xl border border-white/5">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider font-semibold">Proposed Email</p>
                        <p className="text-sm text-foreground font-semibold mb-2">{approval.context_data.subject}</p>
                        <p className="text-xs text-foreground/80 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                          {approval.context_data.body}
                        </p>
                      </div>
                    ) : (
                      <div className="p-4 bg-black/30 rounded-xl border border-white/5">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider font-semibold">
                          AI Classification: {approval.context_data.category} ({approval.context_data.sentiment}
                          {approval.context_data.confidence != null && `, ${Math.round(approval.context_data.confidence * 100)}% confident`})
                        </p>
                        {approval.context_data.summary && (
                          <p className="text-sm text-foreground/90 mb-2">{approval.context_data.summary}</p>
                        )}
                        <p className="text-xs text-foreground/80 whitespace-pre-wrap leading-relaxed max-h-40 overflow-y-auto">
                          {approval.context_data.body}
                        </p>
                        {approval.context_data.next_action && (
                          <p className="text-xs text-primary mt-2 font-medium">Suggested next action: {approval.context_data.next_action}</p>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="p-4 bg-black/30 rounded-xl border border-white/5 mb-6 flex-1">
                    <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider font-semibold">Target Item ID</p>
                    <p className="font-mono text-xs text-primary truncate" title={approval.item_id}>
                      {approval.item_id}
                    </p>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4 mt-auto">
                  <button 
                    onClick={() => mutation.mutate({ id: approval.id, status: 'rejected' })}
                    disabled={mutation.isPending}
                    className="flex items-center justify-center gap-2 py-3 rounded-xl font-medium transition-all border border-destructive/30 text-destructive hover:bg-destructive/10 hover:border-destructive/50 hover:shadow-[0_0_15px_rgba(239,68,68,0.2)]"
                  >
                    <XCircle className="w-4 h-4" /> Reject
                  </button>
                  <button 
                    onClick={() => mutation.mutate({ id: approval.id, status: 'approved' })}
                    disabled={mutation.isPending}
                    className="flex items-center justify-center gap-2 py-3 rounded-xl font-medium transition-all bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 hover:border-emerald-500/50 hover:shadow-[0_0_15px_rgba(16,185,129,0.3)]"
                  >
                    <CheckCircle2 className="w-4 h-4" /> Approve
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}
