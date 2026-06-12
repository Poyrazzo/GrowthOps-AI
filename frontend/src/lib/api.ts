// Django is exposed on host port 18000 by docker-compose (not the in-container 8000)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:18000/api/crm";

export interface Campaign {
  id: string;
  name: string;
  target_sector: string;
  target_country: string;
  target_persona: string;
  value_proposition: string;
  lead_magnet?: string;
  outreach_channel: 'email' | 'linkedin';
  success_metric?: string;
  start_date?: string;
  end_date?: string;
  status: 'draft' | 'active' | 'paused' | 'completed';
  created_at: string;
  updated_at: string;
}

export async function fetchCampaigns(): Promise<Campaign[]> {
  const response = await fetch(`${API_BASE_URL}/campaigns/`);
  if (!response.ok) throw new Error("Failed to fetch campaigns");
  return response.json();
}

export async function createCampaign(data: Partial<Campaign>): Promise<Campaign> {
  const response = await fetch(`${API_BASE_URL}/campaigns/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error("Failed to create campaign");
  return response.json();
}

export interface Lead {
  id: string;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  title: string | null;
  linkedin_url: string | null;
  profile_url: string | null;
  company: string | null;
  company_name: string | null;
  campaign: string | null;
  campaign_name: string | null;
  source_url: string | null;
  persona: string | null;
  department: string | null;
  lead_score: number;
  score_reason: string;
  recommended_message_angle: string;
  requires_human_review: boolean;
  status: 'uncontacted' | 'in_sequence' | 'replied' | 'disqualified';
  created_at: string;
  updated_at: string;
}

export async function fetchLeads(campaignId?: string): Promise<Lead[]> {
  const url = campaignId
    ? `${API_BASE_URL}/leads/?campaign=${campaignId}`
    : `${API_BASE_URL}/leads/`;
  const response = await fetch(url);
  if (!response.ok) throw new Error("Failed to fetch leads");
  return response.json();
}

export async function deleteLead(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/leads/${id}/`, { method: "DELETE" });
  if (!response.ok) throw new Error("Failed to delete lead");
}

export async function queueLeadDraft(id: string): Promise<{ detail: string }> {
  const response = await fetch(`${API_BASE_URL}/leads/${id}/draft/`, { method: "POST" });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to queue drafting");
  }
  return response.json();
}

export async function bulkDeleteLeads(params: { ids?: string[]; campaign?: string }): Promise<{ detail: string }> {
  const response = await fetch(`${API_BASE_URL}/leads/bulk_delete/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!response.ok) throw new Error("Failed to bulk delete leads");
  return response.json();
}

export interface ApprovalContext {
  kind: 'message_draft' | 'reply_review';
  subject?: string;
  body: string;
  category?: string;
  sentiment?: string;
  confidence?: number;
  summary?: string;
  next_action?: string;
  lead_name: string;
  lead_email: string | null;
  lead_title: string | null;
  lead_score: number;
  score_reason: string;
}

export interface ApprovalItem {
  id: string;
  item_type: string;
  item_id: string;
  status: 'pending' | 'approved' | 'rejected';
  reason_for_review: string;
  context_data: ApprovalContext | null;
  created_at: string;
  updated_at: string;
}

export async function fetchApprovals(): Promise<ApprovalItem[]> {
  const response = await fetch(`${API_BASE_URL}/approvals/`);
  if (!response.ok) throw new Error("Failed to fetch approvals");
  return response.json();
}

export async function updateApprovalStatus(id: string, status: 'approved' | 'rejected'): Promise<ApprovalItem> {
  const response = await fetch(`${API_BASE_URL}/approvals/${id}/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  if (!response.ok) throw new Error("Failed to update approval status");
  return response.json();
}

export interface LinkedInTask {
  id: string;
  lead: string; 
  campaign: string;
  lead_name: string;
  lead_linkedin_url: string | null;
  task_type: 'connect' | 'message' | 'engagement';
  status: 'pending' | 'completed' | 'failed';
  instructions: string;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export async function fetchLinkedInTasks(): Promise<LinkedInTask[]> {
  const response = await fetch(`${API_BASE_URL}/linkedintasks/`);
  if (!response.ok) throw new Error("Failed to fetch LinkedIn tasks");
  return response.json();
}

export async function updateLinkedInTaskStatus(id: string, status: 'completed' | 'failed'): Promise<LinkedInTask> {
  const response = await fetch(`${API_BASE_URL}/linkedintasks/${id}/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  if (!response.ok) throw new Error("Failed to update LinkedIn task status");
  return response.json();
}

export interface LeadSource {
  id: string;
  url: string;
  source_type: 'static' | 'dynamic' | 'linkedin' | 'directory';
  sector: string;
  expected_data_fields: Record<string, unknown>;
  access_rules: string;
  priority_score: number;
  campaign: string | null;
  campaign_name: string | null;
  last_scraped_at: string | null;
  created_at: string;
  updated_at: string;
}

export async function fetchLeadSources(campaignId?: string): Promise<LeadSource[]> {
  const url = campaignId
    ? `${API_BASE_URL}/leadsources/?campaign=${campaignId}`
    : `${API_BASE_URL}/leadsources/`;
  const response = await fetch(url);
  if (!response.ok) throw new Error("Failed to fetch lead sources");
  return response.json();
}

export async function createLeadSource(data: {
  url: string;
  source_type: LeadSource['source_type'];
  sector: string;
  priority_score?: number;
  campaign?: string | null;
}): Promise<LeadSource> {
  const response = await fetch(`${API_BASE_URL}/leadsources/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error("Failed to create lead source");
  return response.json();
}

export async function triggerScrape(sourceId: string): Promise<{ detail: string; task_id: string }> {
  const response = await fetch(`${API_BASE_URL}/leadsources/${sourceId}/scrape/`, { method: "POST" });
  if (!response.ok) throw new Error("Failed to trigger scrape");
  return response.json();
}

export async function runCampaignNow(campaignId: string): Promise<{ detail: string }> {
  const response = await fetch(`${API_BASE_URL}/campaigns/${campaignId}/scrape_now/`, { method: "POST" });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to run campaign");
  }
  return response.json();
}

export interface ActivityEntry {
  id: string;
  lead: string;
  lead_name: string | null;
  campaign: string | null;
  activity_type: string;
  description: string;
  created_at: string;
}

export async function fetchActivities(campaignId?: string): Promise<ActivityEntry[]> {
  const url = campaignId
    ? `${API_BASE_URL}/activities/?campaign=${campaignId}`
    : `${API_BASE_URL}/activities/`;
  const response = await fetch(url);
  if (!response.ok) throw new Error("Failed to fetch activities");
  return response.json();
}
