"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle, Clock, AlertCircle, Activity, Target, Mail, Eye, Pencil, X, Loader2 } from "lucide-react";

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

function EditCampaignModal({
  campaign,
  onClose,
  onSave,
}: {
  campaign: any;
  onClose: () => void;
  onSave: (updated: any) => void;
}) {
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    target_persona: campaign.target_persona || "",
    target_sector: campaign.target_sector || "",
    target_country: campaign.target_country || "",
    value_proposition: campaign.value_proposition || "",
  });

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/campaigns/${campaign.id}/`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        }
      );
      if (res.ok) {
        const updated = await res.json();
        onSave(updated);
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <AnimatePresence>
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
        className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-card/90 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl p-6 z-50"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-foreground">Edit Campaign</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/5 rounded-full transition-colors text-muted-foreground hover:text-foreground"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSave} className="space-y-4">
          <div className="space-y-1">
            <label className="text-sm font-medium text-muted-foreground">Target Persona</label>
            <textarea
              rows={3}
              value={form.target_persona}
              onChange={(e) => setForm({ ...form, target_persona: e.target.value })}
              className="w-full bg-black/20 border border-white/10 rounded-lg p-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
              placeholder="e.g. English Language Teachers, HR Managers, Training Directors"
            />
            <p className="text-xs text-muted-foreground">
              Separate multiple personas with commas. The scraper and LinkedIn search use this to find the right people.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-muted-foreground">Target Sector</label>
              <input
                type="text"
                value={form.target_sector}
                onChange={(e) => setForm({ ...form, target_sector: e.target.value })}
                className="w-full bg-black/20 border border-white/10 rounded-lg p-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="e.g. Education, Language Schools"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-muted-foreground">Target Country</label>
              <input
                type="text"
                value={form.target_country}
                onChange={(e) => setForm({ ...form, target_country: e.target.value })}
                className="w-full bg-black/20 border border-white/10 rounded-lg p-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="e.g. Turkey"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-muted-foreground">Value Proposition</label>
            <textarea
              rows={3}
              value={form.value_proposition}
              onChange={(e) => setForm({ ...form, value_proposition: e.target.value })}
              className="w-full bg-black/20 border border-white/10 rounded-lg p-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
              placeholder="We help English teachers improve their students' speaking..."
            />
          </div>

          <div className="pt-2 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors flex items-center gap-2"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              Save Changes
            </button>
          </div>
        </form>
      </motion.div>
    </AnimatePresence>
  );
}

export default function CampaignDetail() {
  const params = useParams();
  const campaignId = params.id as string;
  const [campaign, setCampaign] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [currentPhase, setCurrentPhase] = useState<string>('scraping');
  const [activities, setActivities] = useState<any[]>([]);
  const [editOpen, setEditOpen] = useState(false);

  useEffect(() => {
    const fetchCampaignData = async () => {
      try {
        const base = process.env.NEXT_PUBLIC_API_URL;
        const [campaignRes, leadsRes, messagesRes, activitiesRes] = await Promise.all([
          fetch(`${base}/campaigns/${campaignId}/`),
          fetch(`${base}/leads/?campaign=${campaignId}`),
          fetch(`${base}/messages/?campaign=${campaignId}`),
          fetch(`${base}/activities/?campaign=${campaignId}`),
        ]);
        const campaignData = await campaignRes.json();
        const leads = await leadsRes.json();
        const messages = await messagesRes.json();
        const activityLog = await activitiesRes.json();

        setCampaign(campaignData);

        const draftCount = messages.filter((m: any) => m.status === "needs_review").length;
        const pendingCount = messages.filter((m: any) => m.status === "pending").length;
        const sentCount = messages.filter((m: any) => m.status === "sent").length;
        const repliedCount = leads.filter((l: any) => l.status === "replied").length;

        setMetrics({
          totalLeads: leads.length || 0,
          draftMessages: draftCount,
          sentMessages: sentCount,
          repliedLeads: repliedCount,
        });

        if (repliedCount > 0 || sentCount > 0) setCurrentPhase('tracking');
        else if (pendingCount > 0) setCurrentPhase('sending');
        else if (draftCount > 0) setCurrentPhase('approvals');
        else if (leads.length > 0) setCurrentPhase('drafting');
        else setCurrentPhase('scraping');

        setActivities(
          activityLog.map((a: any) => ({
            id: a.id,
            action: `${a.activity_type.replace(/_/g, ' ')}${a.lead_name ? ` — ${a.lead_name}` : ''}${a.description ? `: ${a.description}` : ''}`,
            time: new Date(a.created_at).toLocaleString(),
            status: 'completed',
          }))
        );
      } catch (error) {
        console.error("Error fetching campaign data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchCampaignData();
    const interval = setInterval(fetchCampaignData, 10000);
    return () => clearInterval(interval);
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
      {editOpen && (
        <EditCampaignModal
          campaign={campaign}
          onClose={() => setEditOpen(false)}
          onSave={(updated) => {
            setCampaign(updated);
            setEditOpen(false);
          }}
        />
      )}

      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-4"
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-4xl font-bold text-white mb-2">{campaign.name}</h1>
            <p className="text-muted-foreground">{campaign.value_proposition}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setEditOpen(true)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-sm text-muted-foreground hover:text-white transition-colors"
            >
              <Pencil className="w-4 h-4" />
              Edit
            </button>
            <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${statusInfo.bg}`}>
              <StatusIcon className={`w-4 h-4 ${statusInfo.text}`} />
              <span className={`font-semibold capitalize ${statusInfo.text}`}>{campaign.status}</span>
            </div>
          </div>
        </div>

        {/* Campaign Info Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div
            className="bg-card/40 backdrop-blur-md border border-white/5 rounded-lg p-4 cursor-pointer hover:border-white/20 transition-colors group"
            onClick={() => setEditOpen(true)}
            title="Click to edit"
          >
            <p className="text-sm text-muted-foreground flex items-center gap-1">
              Target Persona
              <Pencil className="w-3 h-3 opacity-0 group-hover:opacity-50 transition-opacity" />
            </p>
            <p className="text-sm font-semibold text-white mt-1 line-clamp-3">{campaign.target_persona}</p>
          </div>
          <div
            className="bg-card/40 backdrop-blur-md border border-white/5 rounded-lg p-4 cursor-pointer hover:border-white/20 transition-colors group"
            onClick={() => setEditOpen(true)}
            title="Click to edit"
          >
            <p className="text-sm text-muted-foreground flex items-center gap-1">
              Sector
              <Pencil className="w-3 h-3 opacity-0 group-hover:opacity-50 transition-opacity" />
            </p>
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
          {activities.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No activity yet. Activity appears here as soon as scraping, scoring, or drafting runs.
            </p>
          )}
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
                try {
                  const res = await fetch(
                    `${process.env.NEXT_PUBLIC_API_URL}/campaigns/${campaignId}/scrape_now/`,
                    { method: "POST" }
                  );
                  const data = await res.json();
                  alert(data.detail);
                } catch {
                  alert("Failed to start. Is the campaign active and does it have sources?");
                }
              }}
              className="bg-emerald-500 hover:bg-emerald-600 text-white font-semibold px-6 py-2 rounded-lg transition"
            >
              ▶ Run Now (Scrape All Sources)
            </button>
            <button
              onClick={async () => {
                try {
                  const res = await fetch(
                    `${process.env.NEXT_PUBLIC_API_URL}/email-accounts/dispatch_now/`,
                    { method: "POST" }
                  );
                  const data = await res.json();
                  alert(data.detail);
                } catch {
                  alert("Failed to trigger dispatch. Is the celery worker running?");
                }
              }}
              className="bg-orange-500 hover:bg-orange-600 text-white font-semibold px-6 py-2 rounded-lg transition"
            >
              🚀 Şimdi Gönder
            </button>
            <button
              onClick={async () => {
                try {
                  const res = await fetch(
                    `${process.env.NEXT_PUBLIC_API_URL}/email-accounts/poll_now/`,
                    { method: "POST" }
                  );
                  const data = await res.json();
                  alert(data.detail);
                } catch {
                  alert("Failed to trigger inbox poll. Is the celery worker running?");
                }
              }}
              className="bg-indigo-500 hover:bg-indigo-600 text-white font-semibold px-6 py-2 rounded-lg transition"
            >
              📨 Mail Okumayı Simüle Et
            </button>
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
                      { method: "POST", headers: { "Content-Type": "application/json" } }
                    );
                    if (response.ok) {
                      setCampaign({ ...campaign, status: "active" });
                      alert("Campaign restarted!");
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
                    { method: "POST", headers: { "Content-Type": "application/json" } }
                  );
                  if (response.ok) {
                    setCampaign({ ...campaign, status: "active" });
                    alert("Campaign restarted!");
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
