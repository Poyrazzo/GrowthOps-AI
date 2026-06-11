"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { motion, Variants } from "framer-motion";
import { Plus, Megaphone, Target, MapPin, Search, ChevronRight } from "lucide-react";
import { fetchCampaigns } from "@/lib/api";
import { CampaignModal } from "@/components/ui/campaign-modal";
import { cn } from "@/lib/utils";

export default function CampaignsPage() {
  const router = useRouter();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const { data: campaigns, isLoading, isError } = useQuery({
    queryKey: ["campaigns"],
    queryFn: fetchCampaigns,
  });

  const filteredCampaigns = campaigns?.filter(c => 
    c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.target_sector.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const container: Variants = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const item: Variants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-foreground">Campaigns</h2>
          <p className="text-muted-foreground mt-1">Manage and monitor your outbound marketing campaigns.</p>
        </div>
        <button 
          onClick={() => setIsModalOpen(true)}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-lg shadow-[0_0_20px_rgba(var(--primary),0.4)] hover:bg-primary/90 transition-colors flex items-center gap-2 font-medium"
        >
          <Plus className="w-5 h-5" />
          New Campaign
        </button>
      </div>

      <div className="flex items-center gap-4 py-4">
        <div className="relative w-full max-w-sm">
          <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input 
            type="text" 
            placeholder="Search campaigns..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-card/40 backdrop-blur-md border border-white/10 rounded-xl py-2 pl-10 pr-4 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-48 bg-card/20 border border-white/5 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : isError ? (
        <div className="p-6 bg-destructive/10 border border-destructive/20 rounded-xl text-destructive text-center">
          Failed to load campaigns. Ensure the Django backend is running.
        </div>
      ) : filteredCampaigns?.length === 0 ? (
        <div className="py-24 text-center border border-white/5 rounded-2xl bg-card/10 backdrop-blur-sm">
          <Megaphone className="w-12 h-12 text-muted-foreground mx-auto mb-4 opacity-50" />
          <h3 className="text-lg font-medium text-foreground">No campaigns found</h3>
          <p className="text-muted-foreground mt-1">Create your first campaign to get started.</p>
        </div>
      ) : (
        <motion.div 
          variants={container}
          initial="hidden"
          animate="show"
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {filteredCampaigns?.map((campaign) => (
            <motion.div
              key={campaign.id}
              variants={item}
              whileHover={{ y: -5, transition: { duration: 0.2 } }}
              onClick={() => router.push(`/campaigns/${campaign.id}`)}
              className="bg-card/40 backdrop-blur-md border border-white/5 rounded-2xl p-6 shadow-xl group relative overflow-hidden flex flex-col cursor-pointer hover:border-primary/50 transition-all"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
              
              <div className="flex justify-between items-start mb-4 relative z-10">
                <div className="p-3 bg-white/5 rounded-xl border border-white/5">
                  <Megaphone className="w-6 h-6 text-primary" />
                </div>
                <span className={cn(
                  "px-2.5 py-1 text-xs font-medium rounded-full border",
                  campaign.status === 'active' ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                  campaign.status === 'paused' ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                  campaign.status === 'completed' ? "bg-blue-500/10 text-blue-400 border-blue-500/20" :
                  "bg-white/10 text-muted-foreground border-white/10"
                )}>
                  {campaign.status.charAt(0).toUpperCase() + campaign.status.slice(1)}
                </span>
              </div>
              
              <h3 className="text-xl font-bold text-foreground mb-1 relative z-10 truncate" title={campaign.name}>
                {campaign.name}
              </h3>
              
              <div className="space-y-2 mt-4 flex-1 relative z-10">
                <div className="flex items-center text-sm text-muted-foreground gap-2">
                  <Target className="w-4 h-4 shrink-0 text-primary/70" />
                  <span className="truncate">{campaign.target_persona} in {campaign.target_sector}</span>
                </div>
                <div className="flex items-center text-sm text-muted-foreground gap-2">
                  <MapPin className="w-4 h-4 shrink-0 text-primary/70" />
                  <span className="truncate">{campaign.target_country}</span>
                </div>
              </div>
              
              <div className="mt-6 pt-4 border-t border-white/5 flex items-center justify-between text-sm relative z-10">
                <span className="text-muted-foreground">Channel: <span className="text-foreground capitalize">{campaign.outreach_channel}</span></span>
                <span className="text-muted-foreground">{new Date(campaign.created_at).toLocaleDateString()}</span>
              </div>

              <div className="mt-4 pt-4 border-t border-white/5 flex items-center justify-between relative z-10">
                <span className="text-xs text-muted-foreground">Click to view details & monitor</span>
                <ChevronRight className="w-4 h-4 text-primary group-hover:translate-x-1 transition-transform" />
              </div>
            </motion.div>
          ))}
        </motion.div>
      )}

      <CampaignModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  );
}
