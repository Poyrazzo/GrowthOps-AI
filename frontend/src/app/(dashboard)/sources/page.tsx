"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, Variants } from "framer-motion";
import { LayoutList, Search, ShieldAlert, Globe, FileCode2, BookOpen, Users, Megaphone, PlayCircle, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { fetchLeadSources, triggerScrape } from "@/lib/api";
import { SourceModal } from "@/components/ui/source-modal";
import { cn } from "@/lib/utils";

type ScrapeState = 'idle' | 'loading' | 'success' | 'error';

export default function SourcesPage() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [scrapeStates, setScrapeStates] = useState<Record<string, ScrapeState>>({});
  // Read ?campaign= once on mount (set when arriving via "View Sources" on a campaign)
  const [campaignFilter] = useState<string | null>(() =>
    typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("campaign") : null
  );

  const { data: sources, isLoading, isError } = useQuery({
    queryKey: ["lead_sources", campaignFilter],
    queryFn: () => fetchLeadSources(campaignFilter ?? undefined),
  });

  const handleScrapeNow = async (sourceId: string) => {
    setScrapeStates(s => ({ ...s, [sourceId]: 'loading' }));
    try {
      await triggerScrape(sourceId);
      queryClient.invalidateQueries({ queryKey: ["lead_sources"] });
      setScrapeStates(s => ({ ...s, [sourceId]: 'success' }));
      setTimeout(() => setScrapeStates(s => ({ ...s, [sourceId]: 'idle' })), 3000);
    } catch {
      setScrapeStates(s => ({ ...s, [sourceId]: 'error' }));
      setTimeout(() => setScrapeStates(s => ({ ...s, [sourceId]: 'idle' })), 4000);
    }
  };

  const filteredSources = sources?.filter(s =>
    s.url.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.sector.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.campaign_name?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const container: Variants = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const item: Variants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
  };

  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'static': return <FileCode2 className="w-5 h-5" />;
      case 'dynamic': return <Globe className="w-5 h-5" />;
      case 'linkedin': return <Users className="w-5 h-5" />;
      case 'directory': return <BookOpen className="w-5 h-5" />;
      default: return <Globe className="w-5 h-5" />;
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
            <LayoutList className="w-8 h-8 text-primary" />
            Lead Source Manager
          </h2>
          <p className="text-muted-foreground mt-1">
            Configure and monitor the automated scraping pipelines.
            {campaignFilter && <span className="text-primary"> Filtered by campaign.</span>}
          </p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="bg-primary hover:bg-primary/90 text-primary-foreground px-6 py-2.5 rounded-xl font-medium shadow-[0_0_20px_rgba(var(--primary),0.3)] transition-all hover:scale-105 active:scale-95"
        >
          Add Source
        </button>
      </div>

      <div className="flex items-center gap-4 py-4">
        <div className="relative w-full max-w-sm">
          <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search sources by URL, sector, or campaign..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-card/40 backdrop-blur-md border border-white/10 rounded-xl py-2 pl-10 pr-4 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-64 rounded-2xl bg-white/5 animate-pulse border border-white/10" />
          ))}
        </div>
      ) : isError ? (
        <div className="p-8 text-center text-destructive flex flex-col items-center bg-destructive/10 border border-destructive/20 rounded-2xl">
          <ShieldAlert className="w-12 h-12 mb-3 opacity-80" />
          <p className="text-lg font-medium">Failed to load Lead Sources.</p>
        </div>
      ) : filteredSources?.length === 0 ? (
        <div className="p-16 text-center text-muted-foreground bg-card/40 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl">
          <Globe className="w-16 h-16 mx-auto mb-4 opacity-20 text-primary" />
          <p className="text-xl font-semibold text-foreground">No Sources Found.</p>
          <p className="text-sm mt-2">Add your first target website to begin scraping.</p>
        </div>
      ) : (
        <motion.div
          variants={container}
          initial="hidden"
          animate="show"
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {filteredSources?.map((source) => (
            <motion.div
              key={source.id}
              variants={item}
              className="bg-card/40 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col group relative hover:border-white/20 transition-all"
            >
              <div className="h-1 w-full bg-gradient-to-r from-primary to-emerald-400" />
              <div className="p-6 flex-1 flex flex-col">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
                    {getSourceIcon(source.source_type)}
                  </div>
                  <div className="truncate">
                    <h3 className="font-bold text-foreground capitalize">{source.source_type.replace('_', ' ')} Source</h3>
                    <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">{source.sector}</p>
                  </div>
                </div>

                {/* Which campaign owns this source */}
                <div className="mb-4 flex items-center gap-2 text-sm">
                  <Megaphone className="w-4 h-4 shrink-0 text-primary/70" />
                  <span className={cn("truncate", source.campaign_name ? "text-foreground" : "text-amber-400")}>
                    {source.campaign_name || "No campaign — never auto-scraped"}
                  </span>
                </div>

                <div className="mb-6 flex-1">
                  <h4 className="text-xs uppercase tracking-wider font-semibold text-primary/80 mb-2">Target URL</h4>
                  <p className="text-foreground/90 text-sm truncate font-mono bg-black/30 p-2 rounded-lg border border-white/5">
                    {source.url}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4 mt-auto">
                  <div className="bg-white/5 p-3 rounded-xl border border-white/5 text-center">
                    <p className="text-xs text-muted-foreground mb-1">Priority</p>
                    <p className={cn(
                      "font-bold text-lg",
                      source.priority_score >= 80 ? "text-emerald-400" :
                      source.priority_score >= 50 ? "text-amber-400" : "text-white"
                    )}>{source.priority_score}</p>
                  </div>
                  <div className="bg-white/5 p-3 rounded-xl border border-white/5 text-center flex flex-col justify-center">
                    <p className="text-xs text-muted-foreground mb-1">Last scraped</p>
                    <p className="text-xs font-semibold text-foreground">
                      {source.last_scraped_at
                        ? new Date(source.last_scraped_at).toLocaleString()
                        : "Never"}
                    </p>
                  </div>
                </div>

                {source.source_type !== 'linkedin' && (() => {
                  const state = scrapeStates[source.id] ?? 'idle';
                  return (
                    <button
                      onClick={() => handleScrapeNow(source.id)}
                      disabled={state === 'loading'}
                      className={cn(
                        "mt-4 w-full py-2.5 rounded-xl font-medium flex items-center justify-center gap-2 transition-all border disabled:opacity-50",
                        state === 'success'
                          ? "bg-green-500/20 border-green-500/40 text-green-400"
                          : state === 'error'
                          ? "bg-red-500/20 border-red-500/40 text-red-400"
                          : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20"
                      )}
                    >
                      {state === 'loading' && <Loader2 className="w-4 h-4 animate-spin" />}
                      {state === 'success' && <CheckCircle2 className="w-4 h-4" />}
                      {state === 'error' && <XCircle className="w-4 h-4" />}
                      {state === 'idle' && <PlayCircle className="w-4 h-4" />}
                      {state === 'loading' ? 'Queuing…' : state === 'success' ? 'Queued! Check Activity' : state === 'error' ? 'Failed — try again' : 'Scrape Now'}
                    </button>
                  );
                })()}
              </div>
            </motion.div>
          ))}
        </motion.div>
      )}

      <SourceModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} defaultCampaignId={campaignFilter} />
    </div>
  );
}
