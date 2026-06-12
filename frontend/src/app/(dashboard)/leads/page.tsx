"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, Variants } from "framer-motion";
import { Search, Filter, Mail, ShieldAlert, Trash2, ExternalLink } from "lucide-react";
import { fetchLeads, deleteLead, Lead } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LeadSlideover } from "@/components/ui/lead-slideover";

export default function LeadsPage() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  const { data: leads, isLoading, isError } = useQuery({
    queryKey: ["leads"],
    queryFn: () => fetchLeads(),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteLead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      setSelectedLead(null);
    },
  });

  const handleDelete = (lead: Lead) => {
    const name = `${lead.first_name || ""} ${lead.last_name || ""}`.trim() || lead.email || lead.profile_url || lead.linkedin_url;
    if (confirm(`Delete lead "${name}"? This also removes their messages and approval entries.`)) {
      deleteMutation.mutate(lead.id);
    }
  };

  const filteredLeads = leads?.filter(l =>
    (l.first_name + " " + l.last_name).toLowerCase().includes(searchQuery.toLowerCase()) ||
    l.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    l.profile_url?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    l.linkedin_url?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    l.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    l.campaign_name?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const container: Variants = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.05 } }
  };

  const item: Variants = {
    hidden: { opacity: 0, x: -20 },
    show: { opacity: 1, x: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-foreground">Lead Database</h2>
          <p className="text-muted-foreground mt-1">Review AI-enriched leads and orchestrate your outbound pipeline.</p>
        </div>
      </div>

      <div className="flex items-center gap-4 py-4">
        <div className="relative w-full max-w-sm">
          <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input 
            type="text" 
            placeholder="Search leads by name, email, or title..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-card/40 backdrop-blur-md border border-white/10 rounded-xl py-2 pl-10 pr-4 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
          />
        </div>
        <button className="px-4 py-2 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-colors flex items-center gap-2 text-sm font-medium">
          <Filter className="w-4 h-4" /> Filters
        </button>
      </div>

      <div className="bg-card/40 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
        {/* Table Header */}
        <div className="grid grid-cols-12 gap-4 p-4 border-b border-white/10 bg-black/20 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          <div className="col-span-3">Prospect</div>
          <div className="col-span-2">Title / Persona</div>
          <div className="col-span-2">Campaign</div>
          <div className="col-span-1 text-center">Score</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-1 text-right">Added</div>
          <div className="col-span-1 text-right">Actions</div>
        </div>

        {/* Table Body */}
        {isLoading ? (
          <div className="divide-y divide-white/5">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="h-16 bg-white/5 animate-pulse" />
            ))}
          </div>
        ) : isError ? (
          <div className="p-8 text-center text-destructive flex flex-col items-center">
            <ShieldAlert className="w-10 h-10 mb-2 opacity-50" />
            <p>Failed to load leads from database.</p>
          </div>
        ) : filteredLeads?.length === 0 ? (
          <div className="p-16 text-center text-muted-foreground">
            <Mail className="w-12 h-12 mx-auto mb-4 opacity-20" />
            <p className="text-lg">No leads match your search criteria.</p>
          </div>
        ) : (
          <motion.div 
            variants={container}
            initial="hidden"
            animate="show"
            className="divide-y divide-white/5"
          >
            {filteredLeads?.map((lead) => (
              (() => {
                const displayName = `${lead.first_name || ""} ${lead.last_name || ""}`.trim() || "Unnamed Prospect";
                const contactUrl = lead.linkedin_url || lead.profile_url;
                let contactHost = "";
                if (contactUrl) {
                  try {
                    contactHost = new URL(contactUrl).hostname.replace(/^www\./, "");
                  } catch {
                    contactHost = contactUrl;
                  }
                }
                return (
              <motion.div 
                key={lead.id}
                variants={item}
                onClick={() => setSelectedLead(lead)}
                className="grid grid-cols-12 gap-4 p-4 items-center hover:bg-white/5 cursor-pointer transition-colors group relative"
              >
                {/* Subtle left border glow on hover */}
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary scale-y-0 group-hover:scale-y-100 transition-transform origin-left" />
                
                <div className="col-span-3 truncate pl-2">
                  <p className="font-semibold text-foreground truncate">{displayName}</p>
                  <p className="text-xs text-muted-foreground truncate">
                    {lead.email || contactHost || "No contact handle"}
                  </p>
                </div>

                <div className="col-span-2 truncate">
                  <p className="text-sm text-foreground truncate">{lead.title || "Unknown Title"}</p>
                  <p className="text-xs text-muted-foreground truncate">{lead.persona || "Uncategorized"}</p>
                </div>

                <div className="col-span-2 truncate">
                  <p className="text-sm text-foreground truncate" title={lead.campaign_name || undefined}>
                    {lead.campaign_name || "—"}
                  </p>
                  {lead.company_name && (
                    <p className="text-xs text-muted-foreground truncate">{lead.company_name}</p>
                  )}
                </div>

                <div className="col-span-1 flex justify-center">
                  <div className={cn(
                    "flex items-center justify-center w-10 h-10 rounded-full font-bold text-sm border shadow-lg",
                    lead.lead_score >= 80 ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]" :
                    lead.lead_score >= 50 ? "bg-amber-500/20 text-amber-400 border-amber-500/30" :
                    "bg-white/5 text-muted-foreground border-white/10"
                  )}>
                    {lead.lead_score}
                  </div>
                </div>

                <div className="col-span-2">
                  <span className={cn(
                    "px-2.5 py-1 text-xs font-medium rounded-full border",
                    lead.status === 'uncontacted' ? "bg-blue-500/10 text-blue-400 border-blue-500/20" :
                    lead.status === 'in_sequence' ? "bg-primary/10 text-primary border-primary/20" :
                    lead.status === 'replied' ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                    "bg-destructive/10 text-destructive border-destructive/20"
                  )}>
                    {lead.status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </span>
                </div>

                <div className="col-span-1 text-right text-sm text-muted-foreground">
                  {new Date(lead.created_at).toLocaleDateString()}
                </div>

                <div className="col-span-1 flex justify-end">
                  {contactUrl && (
                    <a
                      href={contactUrl}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      title="Open profile"
                      className="p-2 rounded-lg text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(lead); }}
                    disabled={deleteMutation.isPending}
                    title="Delete lead"
                    className="p-2 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
                );
              })()
            ))}
          </motion.div>
        )}
      </div>

      <LeadSlideover lead={selectedLead} onClose={() => setSelectedLead(null)} onDelete={handleDelete} />
    </div>
  );
}
