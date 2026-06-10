const API_BASE_URL = "http://127.0.0.1:8000/api";

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
  company: string | null;
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

export async function fetchLeads(): Promise<Lead[]> {
  const response = await fetch(`${API_BASE_URL}/leads/`);
  if (!response.ok) throw new Error("Failed to fetch leads");
  return response.json();
}

export interface ApprovalItem {
  id: string;
  item_type: string;
  item_id: string;
  status: 'pending' | 'approved' | 'rejected';
  reason_for_review: string;
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
  expected_data_fields: Record<string, any>;
  access_rules: string;
  priority_score: number;
  created_at: string;
  updated_at: string;
}

export async function fetchLeadSources(): Promise<LeadSource[]> {
  const response = await fetch(`${API_BASE_URL}/leadsources/`);
  if (!response.ok) throw new Error("Failed to fetch lead sources");
  return response.json();
}
