"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createLeadSource, fetchCampaigns, LeadSource } from "@/lib/api";

interface SourceModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultCampaignId?: string | null;
}

export function SourceModal({ isOpen, onClose, defaultCampaignId }: SourceModalProps) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<{
    url: string;
    source_type: LeadSource["source_type"];
    sector: string;
    priority_score: number;
    campaign: string;
  }>({
    url: "",
    source_type: "static",
    sector: "",
    priority_score: 50,
    campaign: defaultCampaignId || "",
  });

  const { data: campaigns } = useQuery({
    queryKey: ["campaigns"],
    queryFn: fetchCampaigns,
    enabled: isOpen,
  });

  const mutation = useMutation({
    mutationFn: createLeadSource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lead_sources"] });
      onClose();
      setFormData({ url: "", source_type: "static", sector: "", priority_score: 50, campaign: defaultCampaignId || "" });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      url: formData.url,
      source_type: formData.source_type,
      sector: formData.sector,
      priority_score: formData.priority_score,
      campaign: formData.campaign || null,
    });
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
              <h2 className="text-2xl font-bold text-foreground">Add Lead Source</h2>
              <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full transition-colors text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1">
                <label className="text-sm font-medium text-muted-foreground">URL to scrape</label>
                <input required type="url" value={formData.url} onChange={(e) => setFormData({ ...formData, url: e.target.value })} className="w-full bg-black/20 border border-white/10 rounded-lg p-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" placeholder="https://example.com/contact" />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-sm font-medium text-muted-foreground">Type</label>
                  <select value={formData.source_type} onChange={(e) => setFormData({ ...formData, source_type: e.target.value as LeadSource["source_type"] })} className="w-full bg-black/20 border border-white/10 rounded-lg p-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50">
                    <option value="static">Static (plain HTML)</option>
                    <option value="dynamic">Dynamic (JS-heavy)</option>
                    <option value="directory">Directory / listing</option>
                    <option value="linkedin">LinkedIn (manual only)</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium text-muted-foreground">Sector</label>
                  <input required type="text" value={formData.sector} onChange={(e) => setFormData({ ...formData, sector: e.target.value })} className="w-full bg-black/20 border border-white/10 rounded-lg p-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" placeholder="e.g. Education" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-sm font-medium text-muted-foreground">Priority (0–100)</label>
                  <input type="number" min={0} max={100} value={formData.priority_score} onChange={(e) => setFormData({ ...formData, priority_score: Number(e.target.value) })} className="w-full bg-black/20 border border-white/10 rounded-lg p-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium text-muted-foreground">Campaign</label>
                  <select value={formData.campaign} onChange={(e) => setFormData({ ...formData, campaign: e.target.value })} className="w-full bg-black/20 border border-white/10 rounded-lg p-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50">
                    <option value="">No campaign (won't auto-scrape)</option>
                    {campaigns?.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <p className="text-xs text-muted-foreground">
                Sources without a campaign are never auto-scraped. LinkedIn sources are never scraped (manual tasks only).
              </p>

              {mutation.isError && (
                <p className="text-sm text-destructive">Failed to create source. Is the URL already registered?</p>
              )}

              <div className="pt-2 flex justify-end gap-3">
                <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors">
                  Cancel
                </button>
                <button type="submit" disabled={mutation.isPending} className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-[0_0_15px_rgba(var(--primary),0.3)] flex items-center gap-2">
                  {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  Add Source
                </button>
              </div>
            </form>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
