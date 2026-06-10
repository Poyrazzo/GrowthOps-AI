"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2 } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createCampaign } from "@/lib/api";

interface CampaignModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CampaignModal({ isOpen, onClose }: CampaignModalProps) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<{
    name: string;
    target_sector: string;
    target_country: string;
    target_persona: string;
    value_proposition: string;
    outreach_channel: "email" | "linkedin";
  }>({
    name: "",
    target_sector: "",
    target_country: "",
    target_persona: "",
    value_proposition: "",
    outreach_channel: "email",
  });

  const mutation = useMutation({
    mutationFn: createCampaign,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      onClose();
      // Reset form
      setFormData({
        name: "",
        target_sector: "",
        target_country: "",
        target_persona: "",
        value_proposition: "",
        outreach_channel: "email",
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate(formData);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-card/80 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl p-6 z-50 overflow-hidden"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-foreground">New Campaign</h2>
              <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full transition-colors text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1">
                <label className="text-sm font-medium text-muted-foreground">Campaign Name</label>
                <input required type="text" value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})} className="w-full bg-black/20 border border-white/10 rounded-lg p-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" placeholder="e.g. Q3 Enterprise Push" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-sm font-medium text-muted-foreground">Target Sector</label>
                  <input required type="text" value={formData.target_sector} onChange={(e) => setFormData({...formData, target_sector: e.target.value})} className="w-full bg-black/20 border border-white/10 rounded-lg p-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" placeholder="e.g. SaaS" />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium text-muted-foreground">Target Country</label>
                  <input required type="text" value={formData.target_country} onChange={(e) => setFormData({...formData, target_country: e.target.value})} className="w-full bg-black/20 border border-white/10 rounded-lg p-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" placeholder="e.g. US" />
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-muted-foreground">Target Persona</label>
                <input required type="text" value={formData.target_persona} onChange={(e) => setFormData({...formData, target_persona: e.target.value})} className="w-full bg-black/20 border border-white/10 rounded-lg p-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" placeholder="e.g. VP of Sales" />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-muted-foreground">Value Proposition</label>
                <textarea required rows={3} value={formData.value_proposition} onChange={(e) => setFormData({...formData, value_proposition: e.target.value})} className="w-full bg-black/20 border border-white/10 rounded-lg p-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none" placeholder="We help you close 20% more deals..." />
              </div>

              <div className="pt-4 flex justify-end gap-3">
                <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors">
                  Cancel
                </button>
                <button type="submit" disabled={mutation.isPending} className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-[0_0_15px_rgba(var(--primary),0.3)] flex items-center gap-2">
                  {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  Launch Campaign
                </button>
              </div>
            </form>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
