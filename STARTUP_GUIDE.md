# GrowthOps AI - Complete Startup Guide

Complete step-by-step instructions to run the entire system from your own terminals.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Project Setup](#project-setup)
3. [Start Services](#start-services)
4. [Initialize Database](#initialize-database)
5. [Create Initial Data](#create-initial-data)
6. [Verify Setup](#verify-setup)
7. [Run a Complete Campaign](#run-a-complete-campaign)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, ensure you have:

- **Docker** and **Docker Compose** installed
- **Git** (for version control)
- **Python 3.11+** (for local development, optional)
- **API Keys**:
  - OpenAI API key (with active credits)
  - Langfuse keys (optional, for observability)
- **Gmail Account** for outreach email (with 2FA enabled)

### Get API Keys

1. **OpenAI**: Go to https://platform.openai.com/account/api-keys
   - Create API key
   - Add payment method at https://platform.openai.com/account/billing/overview
   - Set usage limit ($10-20 is plenty)

2. **Gmail App Password** (if using Gmail for outreach):
   - Go to myaccount.google.com → Security
   - Enable 2-Step Verification
   - Create "App Password" → copy the 16-char password

3. **Langfuse** (optional):
   - Go to https://cloud.langfuse.com
   - Create project → copy public + secret keys

---

## Project Setup

### Terminal 1: Clone & Configure

```bash
# Navigate to project directory
cd /path/to/GrowthOps\ AI

# Create .env file with your API keys
cat > .env << 'EOF'
OPENAI_API_KEY=sk-your-openai-key-here
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_HOST=https://cloud.langfuse.com

# Outreach email account
OUTREACH_EMAIL=your-email@gmail.com
OUTREACH_APP_PASSWORD=your-16-char-app-password

# AdsPower (optional)
ADSPOWER_PROFILE_ID=your-profile-id

# Django SECRET_KEY (already generated)
DJANGO_SECRET_KEY=(0e=7tr=s8a=$^&uy)e$!209@es0wykbyt6f5*rj#7*l=+uss+
EOF

# Verify .env was created
cat .env
```

---

## Start Services

### Terminal 2: Start Docker Services

```bash
cd /path/to/GrowthOps\ AI

# Build and start all containers
docker compose up -d --build

# Watch the logs
docker compose logs -f

# In a few moments, you'll see:
# - postgres starting
# - redis starting
# - django runserver at 0.0.0.0:8000
# - frontend at 0.0.0.0:3000
# - celery worker ready

# Once logs show "django ready", proceed to next step
```

**Wait for all services to be healthy** (takes ~30-60 seconds).

---

## Initialize Database

### Terminal 1: Run Migrations & Setup

```bash
cd /path/to/GrowthOps\ AI

# Apply database migrations
docker compose exec django python manage.py migrate

# Output should show:
# Running migrations:
#   No migrations to apply.
# (This is expected since migrations are pre-created)

# Create Django superuser (admin)
docker compose exec django python manage.py shell << 'EOF'
from django.contrib.auth.models import User
User.objects.create_superuser('admin', 'your-email@gmail.com', 'your-password-here')
print('✓ Superuser created: admin')
EOF

# Seed email account (your Gmail)
docker compose exec django python manage.py seed_email_account

# Output:
# Created EmailAccount for your-email@gmail.com
```

### Check Database Status

```bash
# Verify email account was created
docker compose exec django python manage.py shell << 'EOF'
from crm.models import EmailAccount
acc = EmailAccount.objects.first()
print(f'Email Account: {acc.email}')
print(f'SMTP: {acc.smtp_host}:{acc.smtp_port}')
print(f'IMAP: {acc.imap_host}:{acc.imap_port}')
print(f'Active: {acc.is_active}')
EOF
```

---

## Create Initial Data

### Terminal 1: Seed Sample Data

```bash
cd /path/to/GrowthOps\ AI

# Create sample lead magnets
docker compose exec django python manage.py seed_lead_magnets

# Create campaign for Turkish English learning
docker compose exec django python manage.py seed_campaign_turkish

# Create test leads
docker compose exec django python manage.py seed_test_leads

# Verify data
docker compose exec django python manage.py shell << 'EOF'
from crm.models import Campaign, Lead, LeadMagnet, LeadSource

print(f"Campaigns: {Campaign.objects.count()}")
print(f"Leads: {Lead.objects.count()}")
print(f"Lead Magnets: {LeadMagnet.objects.count()}")
print(f"Lead Sources: {LeadSource.objects.count()}")

campaign = Campaign.objects.first()
print(f"\nActive Campaign: {campaign.name}")
print(f"Status: {campaign.status}")
print(f"Leads: {Lead.objects.filter(campaign=campaign).count()}")
EOF
```

---

## Verify Setup

### Terminal 1: Check All Services

```bash
# Check all containers are running
docker compose ps

# Output should show all containers with status "Up":
# - postgres
# - redis
# - django
# - celery_worker
# - celery_beat
# - playwright_worker
# - frontend
# - n8n
# - greenmail

# If any container is not "Up", check logs:
docker compose logs [container-name]
```

### Access the System

Open your browser and test each URL:

1. **Django Admin**: http://localhost:18000/admin/
   - Username: `admin`
   - Password: (whatever you set above)
   - You should see: Campaigns, Leads, Email Accounts, etc.

2. **Dashboard**: http://localhost:3000/
   - Should show "Growth Automation Dashboard"
   - No data yet (that's normal)

3. **Campaigns**: http://localhost:3000/campaigns
   - Should show your Turkish campaign (status: Active)

4. **Leads**: http://localhost:3000/
   - Should show 3 test leads (Ahmet, Fatma, Mehmet)

5. **Approvals**: http://localhost:3000/approvals
   - Should say "Queue is clear" (no drafts yet)

---

## Run a Complete Campaign

### Complete End-to-End Test

#### Step 1: Activate Campaign (Already Active)

```bash
# Your campaign is already ACTIVE from seed_campaign_turkish
# Verify:
docker compose exec django python manage.py shell << 'EOF'
from crm.models import Campaign
campaign = Campaign.objects.first()
print(f"Campaign: {campaign.name}")
print(f"Status: {campaign.status}")
print(f"Leads: {campaign.lead_set.count()}")
print(f"Sources: {campaign.leadsource_set.count()}")
EOF
```

#### Step 2: Create Draft Messages

Messages should be auto-generated after leads are added, but if not, create them manually:

```bash
docker compose exec django python manage.py shell << 'EOF'
from crm.models import Lead, Message, EmailAccount

leads = Lead.objects.filter(status='uncontacted')
email_account = EmailAccount.objects.first()

print(f"Creating {leads.count()} draft messages...\n")

for lead in leads:
    message = Message.objects.create(
        lead=lead,
        campaign=lead.campaign,
        sender_account=email_account,
        channel='email',
        status='needs_review',
        body=f"""Hi {lead.first_name},

I came across your profile and thought Konuşarak Öğren could be perfect for your team.

Our AI-powered English speaking practice platform helps professionals improve fluency through real-time conversation.

Would you be open to a quick 15-minute call to see if it's a fit?

Best regards,
Growth Team""",
        subject=f"English learning opportunity at {lead.company.name if lead.company else 'your organization'}",
    )
    print(f"✓ {lead.first_name} {lead.last_name}")

print(f"\n✓ {leads.count()} drafts created!")
EOF
```

#### Step 3: Approve Messages

1. Open http://localhost:3000/approvals
2. You should see 3 draft messages
3. Click **Approve** on each one

**In your terminal**, verify they moved to pending:

```bash
docker compose exec django python manage.py shell << 'EOF'
from crm.models import Message

pending = Message.objects.filter(status='pending').count()
approved = Message.objects.filter(status='sent').count()
drafts = Message.objects.filter(status='needs_review').count()

print(f"Draft (needs_review): {drafts}")
print(f"Pending (pending): {pending}")
print(f"Sent (sent): {approved}")
EOF
```

#### Step 4: Dispatch Messages

```bash
# Trigger immediate dispatch (normally runs every 10 min)
docker compose exec django python manage.py shell << 'EOF'
from outreach.sequence import dispatch_pending_emails
result = dispatch_pending_emails()
print(f"✓ Dispatched {result} messages")
EOF
```

Check your Gmail inbox (`your-email@gmail.com`) — you should receive 3 emails!

#### Step 5: Simulate Receiving a Reply

```bash
# Create a mock reply (simulates receiving an email)
docker compose exec django python manage.py shell << 'EOF'
from crm.models import Lead, Reply

lead = Lead.objects.first()

reply = Reply.objects.create(
    lead=lead,
    from_email=lead.email,
    body="Yes, I'm very interested! Let's schedule a call.",
    received_at=timezone.now(),
)

lead.status = 'replied'
lead.save()

print(f"✓ Mock reply created for {lead.first_name}")
print(f"Lead status: {lead.status}")
EOF
```

Go to **Lead Database** (http://localhost:3000/) and refresh — the lead status should now show "Replied".

---

## Monitor & Manage

### View Campaign Status

```bash
# Go to: http://localhost:3000/campaigns
# Click your campaign card
# You'll see:
# - Total Leads: 3
# - Drafts Pending: 0
# - Sent: 3
# - Replied: 1
# - Workflow pipeline showing current phase
# - Recent activity feed
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f celery_worker
docker compose logs -f django
docker compose logs -f frontend
```

### Stop Services

```bash
# Stop but keep data
docker compose down

# Stop and delete everything
docker compose down -v
```

### Restart Services

```bash
# Restart one service
docker compose restart django

# Restart all
docker compose restart
```

---

## Troubleshooting

### Problem: "OpenAI quota exceeded"

**Solution:**
1. Go to https://platform.openai.com/account/billing/overview
2. Add payment method
3. Check usage and set usage limit
4. Restart celery: `docker compose restart celery_worker`

### Problem: "Queue is clear" but messages should be there

**Solution:**
1. Celery might not be processing tasks
2. Manually create messages (see Step 2 above)
3. Or restart Celery: `docker compose restart celery_worker`

### Problem: Emails not sending

**Checklist:**
```bash
# 1. Check email account is active
docker compose exec django python manage.py shell << 'EOF'
from crm.models import EmailAccount
acc = EmailAccount.objects.first()
print(f"Active: {acc.is_active}")
print(f"SMTP Host: {acc.smtp_host}")
print(f"SMTP Port: {acc.smtp_port}")
EOF

# 2. Check messages are in "pending" status
docker compose exec django python manage.py shell << 'EOF'
from crm.models import Message
pending = Message.objects.filter(status='pending')
print(f"Pending messages: {pending.count()}")
for msg in pending:
    print(f"  - {msg.lead.email}")
EOF

# 3. Trigger dispatch manually
docker compose exec django python manage.py shell << 'EOF'
from outreach.sequence import dispatch_pending_emails
result = dispatch_pending_emails()
print(f"Dispatched: {result}")
EOF
```

### Problem: Django loads but has errors

**Solution:**
```bash
# View logs
docker compose logs django

# Restart with fresh start
docker compose down
docker compose up -d --build
docker compose exec django python manage.py migrate
```

### Problem: Port already in use

**Solution:**
```bash
# Change port in docker-compose.yml
# or kill existing process:
lsof -i :18000  # Find what's using port 18000
kill -9 [PID]   # Kill the process
```

---

## Key URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Django Admin | http://localhost:18000/admin/ | admin / your-password |
| Dashboard | http://localhost:3000/ | - |
| Campaigns | http://localhost:3000/campaigns | - |
| Leads | http://localhost:3000/ | - |
| Approvals | http://localhost:3000/approvals | - |
| n8n | http://localhost:5678/ | (create on first visit) |

---

## Common Commands

```bash
# Navigate to project
cd /path/to/GrowthOps\ AI

# View all running containers
docker compose ps

# View logs for all services
docker compose logs -f

# View logs for one service
docker compose logs -f django

# Run Django command
docker compose exec django python manage.py [command]

# Open Django shell
docker compose exec django python manage.py shell

# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v

# Restart services
docker compose restart

# View system status
docker compose stats
```

---

## Next Steps

Once the system is running:

1. **Test the full workflow** (Steps 1-5 above)
2. **Pause/Resume campaign** from campaign detail page
3. **Check activity logs** in campaign status page
4. **Modify lead magnets** (Django Admin → Lead Magnets)
5. **Add real lead sources** (Django Admin → Lead Sources)
6. **Configure Slack/Discord webhook** (optional, for alerts)

---

## Support

If you encounter issues:

1. Check logs: `docker compose logs -f [service-name]`
2. Verify all containers are running: `docker compose ps`
3. Check `.env` file has all required keys
4. Ensure API keys have active billing (OpenAI)
5. Restart services: `docker compose restart`

---

**Last Updated:** 2026-06-11
**System:** GrowthOps AI - Growth Automation Platform
