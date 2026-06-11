"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { CheckCircle, Clock, AlertCircle, Activity, Target, Mail, Eye } from "lucide-react";

const statusColors: { [key: string]: { bg: string; text: string; icon: any } } = {
  draft: { bg: "bg-yellow-500/10", text: "text-yellow-400", icon: Clock },
  active: { bg: "bg-green-500/10", text: "text-green-400", icon: CheckCircle },
  paused: { bg: "bg-red-500/10", text: "text-red-400", icon: AlertCircle },
};

const PHASES = [
  { id: 'scraping', label: 'Scraping', description: 'Extracting leads from sources' },
  { id: 'drafting', label: 'Drafting', description: 'AI generating messages' },
  { id: 'approvals', label: 'Approvals', description: 'Awaiting your approval' },
  { id: 'sending', label: 'Sending', description: 'Dispatching emails' },
  { id: 'tracking', label: 'Tracking', description: 'Monitoring replies' },
];

export default function CampaignDetail() {
  const params = useParams();
  const campaignId = params.id as string;
  const [campaign, setCampaign] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [currentPhase, setCurrentPhase] = useState<string>('scraping');
  const [activities, setActivities] = useState<any[]>([
    { id: 1, action: 'Campaign activated', time: 'Now', status: 'completed' },
  ]);

  useEffect(() => {
    const fetchCampaignData = async () => {
      try {
        const campaignRes = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/campaigns/${campaignId}/`
        );
        const campaignData = await campaignRes.json();
        setCampaign(campaignData);

        // Fetch related metrics
        const leadsRes = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/leads/?campaign=${campaignId}`
        );
        const leads = await leadsRes.json();

        const messagesRes = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/messages/?campaign=${campaignId}`
        );
        const messages = await messagesRes.json();

        setMetrics({
          totalLeads: leads.length || 0,
          draftMessages: messages.filter((m: any) => m.status === "needs_review").length || 0,
          sentMessages: messages.filter((m: any) => m.status === "sent").length || 0,
          repliedLeads: leads.filter((l: any) => l.status === "replied").length || 0,
        });
      } catch (error) {
        console.error("Error fetching campaign data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchCampaignData();
  }, [campaignId]);

  if (loading || !campaign) {
    return (
      <div className="max-w-6xl mx-auto py-12">
        <div className="text-center text-muted-foreground">Loading campaign details...</div>
      </div>
    );
  }

  const statusInfo = statusColors[campaign.status] || statusColors.draft;
  const StatusIcon = statusInfo.icon;

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-4"
      >
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">{campaign.name}</h1>
            <p className="text-muted-foreground">{campaign.value_proposition}</p>
          </div>
          <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${statusInfo.bg}`}>
            <StatusIcon className={`w-4 h-4 ${statusInfo.text}`} />
            <span className={`font-semibold capitalize ${statusInfo.text}`}>{campaign.status}</span>
          </div>
        </div>

        {/* Campaign Info Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-card/40 backdrop-blur-md border border-white/5 rounded-lg p-4">
            <p className="text-sm text-muted-foreground">Target Persona</p>
            <p className="text-lg font-semibold text-white mt-1">{campaign.target_persona}</p>
          </div>
          <div className="bg-card/40 backdrop-blur-md border border-white/5 rounded-lg p-4">
            <p className="text-sm text-muted-foreground">Sector</p>
            <p className="text-lg font-semibold text-white mt-1">{campaign.target_sector}</p>
          </div>
          <div className="bg-card/40 backdrop-blur-md border border-white/5 rounded-lg p-4">
            <p className="text-sm text-muted-foreground">Country</p>
            <p className="text-lg font-semibold text-white mt-1">{campaign.target_country}</p>
          </div>
          <div className="bg-card/40 backdrop-blur-md border border-white/5 rounded-lg p-4">
            <p className="text-sm text-muted-foreground">Channel</p>
            <p className="text-lg font-semibold text-white mt-1 capitalize">{campaign.outreach_channel}</p>
          </div>
        </div>
      </motion.div>

      {/* Pipeline Metrics */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="grid grid-cols-1 md:grid-cols-4 gap-4"
      >
        <div className="bg-card/40 backdrop-blur-md border border-white/5 rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-muted-foreground">Total Leads</span>
            <Target className="w-4 h-4 text-blue-400" />
          </div>
          <p className="text-3xl font-bold text-white">{metrics?.totalLeads || 0}</p>
        </div>
        <div className="bg-card/40 backdrop-blur-md border border-white/5 rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-muted-foreground">Drafts Pending</span>
            <Eye className="w-4 h-4 text-yellow-400" />
          </div>
          <p className="text-3xl font-bold text-white">{metrics?.draftMessages || 0}</p>
          <p className="text-xs text-muted-foreground mt-2">Awaiting approval</p>
        </div>
        <div className="bg-card/40 backdrop-blur-md border border-white/5 rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-muted-foreground">Sent</span>
            <Mail className="w-4 h-4 text-green-400" />
          </div>
          <p className="text-3xl font-bold text-white">{metrics?.sentMessages || 0}</p>
        </div>
        <div className="bg-card/40 backdrop-blur-md border border-white/5 rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-muted-foreground">Replied</span>
            <Activity className="w-4 h-4 text-purple-400" />
          </div>
          <p className="text-3xl font-bold text-white">{metrics?.repliedLeads || 0}</p>
        </div>
      </motion.div>

      {/* Workflow Pipeline */}
      {campaign.status === "active" && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="space-y-4"
        >
          <h3 className="text-lg font-semibold text-white">Workflow Pipeline</h3>
          <div className="grid grid-cols-5 gap-2">
            {PHASES.map((phase, idx) => (
              <div key={phase.id} className="flex flex-col items-center">
                <div
                  className={`w-12 h-12 rounded-full flex items-center justify-center mb-2 transition-all ${
                    currentPhase === phase.id
                      ? "bg-blue-500/30 border-2 border-blue-400 animate-pulse"
                      : "bg-card/40 border border-white/10"
                  }`}
                >
                  <span className="text-sm font-bold">{idx + 1}</span>
                </div>
                <p className="text-xs font-medium text-center text-foreground">{phase.label}</p>
                <p className="text-xs text-muted-foreground text-center mt-1">{phase.description}</p>
                {idx < PHASES.length - 1 && (
                  <div className="w-0.5 h-8 bg-white/10 mt-2" />
                )}
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Recent Activity */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="bg-card/40 backdrop-blur-md border border-white/5 rounded-lg p-6"
      >
        <h3 className="text-lg font-semibold text-white mb-4">Recent Activity</h3>
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {activities.map((activity) => (
            <div
              key={activity.id}
              className="flex items-center gap-4 p-3 bg-white/5 rounded-lg border border-white/5"
            >
              <div
                className={`w-2 h-2 rounded-full ${
                  activity.status === "completed"
                    ? "bg-green-400"
                    : activity.status === "running"
                    ? "bg-blue-400 animate-pulse"
                    : "bg-yellow-400"
                }`}
              />
              <div className="flex-1">
                <p className="text-sm text-foreground">{activity.action}</p>
                <p className="text-xs text-muted-foreground">{activity.time}</p>
              </div>
              <span className="text-xs font-medium capitalize text-muted-foreground">
                {activity.status}
              </span>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Campaign Actions */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="flex flex-wrap gap-3"
      >
        {campaign.status === "draft" && (
          <button
            onClick={async () => {
              const res = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/campaigns/${campaignId}/`,
                {
                  method: "PATCH",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ status: "active" }),
                }
              );
              if (res.ok) {
                setCampaign({ ...campaign, status: "active" });
              }
            }}
            className="bg-green-500 hover:bg-green-600 text-white font-semibold px-6 py-2 rounded-lg transition"
          >
            ✓ Activate Campaign
          </button>
        )}

        {campaign.status === "active" && (
          <>
            <button
              onClick={async () => {
                const res = await fetch(
                  `${process.env.NEXT_PUBLIC_API_URL}/campaigns/${campaignId}/`,
                  {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ status: "paused" }),
                  }
                );
                if (res.ok) {
                  setCampaign({ ...campaign, status: "paused" });
                }
              }}
              className="bg-amber-500 hover:bg-amber-600 text-white font-semibold px-6 py-2 rounded-lg transition"
            >
              ⏸ Pause Campaign
            </button>

            <button
              onClick={async () => {
                const res = await fetch(
                  `${process.env.NEXT_PUBLIC_API_URL}/campaigns/${campaignId}/`,
                  {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ status: "completed" }),
                  }
                );
                if (res.ok) {
                  setCampaign({ ...campaign, status: "completed" });
                }
              }}
              className="bg-red-500 hover:bg-red-600 text-white font-semibold px-6 py-2 rounded-lg transition"
            >
              ✗ End Campaign
            </button>
          </>
        )}

        {campaign.status === "paused" && (
          <>
            <button
              onClick={async () => {
                const res = await fetch(
                  `${process.env.NEXT_PUBLIC_API_URL}/campaigns/${campaignId}/`,
                  {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ status: "active" }),
                  }
                );
                if (res.ok) {
                  setCampaign({ ...campaign, status: "active" });
                }
              }}
              className="bg-green-500 hover:bg-green-600 text-white font-semibold px-6 py-2 rounded-lg transition"
            >
              ▶ Resume Campaign
            </button>

            <button
              onClick={async () => {
                if (confirm("Restart campaign? This will reset all lead statuses to uncontacted and re-trigger drafting.")) {
                  try {
                    const response = await fetch(
                      `${process.env.NEXT_PUBLIC_API_URL}/campaigns/${campaignId}/restart/`,
                      {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                      }
                    );
                    if (response.ok) {
                      setCampaign({ ...campaign, status: "active" });
                      alert("Campaign restarted! Leads reset and drafting re-triggered.");
                    }
                  } catch (error) {
                    console.error("Error restarting campaign:", error);
                  }
                }
              }}
              className="bg-purple-500 hover:bg-purple-600 text-white font-semibold px-6 py-2 rounded-lg transition"
            >
              🔄 Restart Campaign
            </button>
          </>
        )}

        {campaign.status === "completed" && (
          <button
            onClick={async () => {
              if (confirm("Restart campaign? This will reset all lead statuses to uncontacted and re-trigger drafting.")) {
                try {
                  const response = await fetch(
                    `${process.env.NEXT_PUBLIC_API_URL}/campaigns/${campaignId}/restart/`,
                    {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                    }
                  );
                  if (response.ok) {
                    setCampaign({ ...campaign, status: "active" });
                    alert("Campaign restarted! Leads reset and drafting re-triggered.");
                  }
                } catch (error) {
                  console.error("Error restarting campaign:", error);
                }
              }
            }}
            className="bg-purple-500 hover:bg-purple-600 text-white font-semibold px-6 py-2 rounded-lg transition"
          >
            🔄 Restart Campaign
          </button>
        )}

        <button
          onClick={() => {
            window.open(`/sources?campaign=${campaignId}`, '_blank');
          }}
          className="bg-blue-500 hover:bg-blue-600 text-white font-semibold px-6 py-2 rounded-lg transition"
        >
          📊 View Sources
        </button>
      </motion.div>
    </div>
  );
}
