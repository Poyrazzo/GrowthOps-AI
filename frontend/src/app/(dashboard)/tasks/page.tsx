"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, Variants } from "framer-motion";
import { Briefcase, CheckCircle2, XCircle, ShieldAlert, Users, ExternalLink, MessageCircle, Link as LinkIcon, ThumbsUp } from "lucide-react";
import { fetchLinkedInTasks, updateLinkedInTaskStatus } from "@/lib/api";

export default function TasksPage() {
  const queryClient = useQueryClient();

  const { data: tasks, isLoading, isError } = useQuery({
    queryKey: ["linkedin_tasks"],
    queryFn: fetchLinkedInTasks,
  });

  const mutation = useMutation({
    mutationFn: ({ id, status }: { id: string, status: 'completed' | 'failed' }) => updateLinkedInTaskStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["linkedin_tasks"] });
    },
  });

  const pendingTasks = tasks?.filter(t => t.status === 'pending') || [];

  const container: Variants = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const item: Variants = {
    hidden: { opacity: 0, scale: 0.95 },
    show: { opacity: 1, scale: 1, transition: { type: "spring", stiffness: 300, damping: 24 } }
  };

  const getTaskIcon = (type: string) => {
    switch (type) {
      case 'connect': return <LinkIcon className="w-5 h-5" />;
      case 'message': return <MessageCircle className="w-5 h-5" />;
      case 'engagement': return <ThumbsUp className="w-5 h-5" />;
      default: return <Users className="w-5 h-5" />;
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
          <Briefcase className="w-8 h-8 text-[#0077b5]" />
          LinkedIn Manual Tasks
        </h2>
        <p className="text-muted-foreground mt-1">Execute specialized social selling tasks orchestrated by the AI.</p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-48 rounded-2xl bg-white/5 animate-pulse border border-white/10" />
          ))}
        </div>
      ) : isError ? (
        <div className="p-8 bg-destructive/10 border border-destructive/20 rounded-2xl text-center text-destructive flex flex-col items-center">
          <ShieldAlert className="w-12 h-12 mb-3 opacity-80" />
          <p className="text-lg font-medium">Failed to load Task Queue.</p>
        </div>
      ) : pendingTasks.length === 0 ? (
        <div className="p-16 text-center text-muted-foreground bg-card/40 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl">
          <CheckCircle2 className="w-16 h-16 mx-auto mb-4 opacity-20 text-emerald-500" />
          <p className="text-xl font-semibold text-foreground">All Caught Up.</p>
          <p className="text-sm mt-2">No pending manual tasks at this time.</p>
        </div>
      ) : (
        <motion.div 
          variants={container}
          initial="hidden"
          animate="show"
          className="grid grid-cols-1 lg:grid-cols-2 gap-6"
        >
          {pendingTasks.map((task) => (
            <motion.div 
              key={task.id}
              variants={item}
              className="bg-card/60 backdrop-blur-xl border border-white/10 rounded-2xl shadow-xl overflow-hidden flex flex-col hover:border-white/20 transition-colors"
            >
              <div className="p-6 flex flex-col flex-1">
                {/* Header */}
                <div className="flex items-center justify-between mb-4 pb-4 border-b border-white/10">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-[#0077b5]/10 flex items-center justify-center text-[#0077b5] border border-[#0077b5]/30 shadow-[0_0_10px_rgba(0,119,181,0.2)]">
                      {getTaskIcon(task.task_type)}
                    </div>
                    <div>
                      <h3 className="font-bold text-foreground capitalize">{task.task_type} Task</h3>
                      <p className="text-xs text-muted-foreground flex items-center gap-1">
                        For <span className="font-medium text-white">{task.lead_name}</span> &bull; Due: {task.due_date ? new Date(task.due_date).toLocaleDateString() : 'ASAP'}
                      </p>
                    </div>
                  </div>
                  {task.lead_linkedin_url ? (
                    <a href={task.lead_linkedin_url} target="_blank" rel="noreferrer" className="text-xs bg-[#0077b5]/10 hover:bg-[#0077b5]/20 text-[#0077b5] font-semibold px-3 py-1.5 rounded-full border border-[#0077b5]/30 flex items-center gap-2 transition-colors">
                      Target Profile <ExternalLink className="w-3 h-3" />
                    </a>
                  ) : (
                    <span className="text-xs bg-white/5 text-muted-foreground px-3 py-1.5 rounded-full border border-white/10 flex items-center gap-2 cursor-not-allowed opacity-50">
                      No URL <ExternalLink className="w-3 h-3" />
                    </span>
                  )}
                </div>

                {/* Instructions */}
                <div className="flex-1 mb-6">
                  <h4 className="text-xs uppercase tracking-wider font-semibold text-primary/80 mb-2">Task Instructions</h4>
                  <div className="p-4 rounded-xl bg-black/40 border border-white/5">
                    <p className="text-sm text-foreground/90 leading-relaxed font-medium">
                      {task.instructions || "No specific instructions provided."}
                    </p>
                  </div>
                </div>

                {/* Actions */}
                <div className="grid grid-cols-2 gap-4 mt-auto">
                  <button 
                    onClick={() => mutation.mutate({ id: task.id, status: 'failed' })}
                    disabled={mutation.isPending}
                    className="flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-all border border-destructive/30 text-destructive hover:bg-destructive/10 hover:border-destructive/50"
                  >
                    <XCircle className="w-4 h-4" /> Mark Failed
                  </button>
                  <button 
                    onClick={() => mutation.mutate({ id: task.id, status: 'completed' })}
                    disabled={mutation.isPending}
                    className="flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-all bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 hover:border-emerald-500/50 hover:shadow-[0_0_15px_rgba(16,185,129,0.3)]"
                  >
                    <CheckCircle2 className="w-4 h-4" /> Mark Complete
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
