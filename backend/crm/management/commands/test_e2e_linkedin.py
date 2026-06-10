from django.core.management.base import BaseCommand
from crm.models import Campaign, Lead, LinkedInTask, AuditLog
from rest_framework.test import APIClient

class Command(BaseCommand):
    help = 'Runs an end-to-end test of the LinkedIn Manual Workflow and CRM state updates.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting E2E LinkedIn Workflow Test...'))

        # 1. Seed Campaign and Lead
        campaign, _ = Campaign.objects.get_or_create(
            name='LinkedIn E2E Test Campaign',
            defaults={
                'target_sector': 'Technology',
                'target_country': 'US',
                'target_persona': 'CTO',
                'value_proposition': 'We automate growth.',
                'outreach_channel': 'linkedin'
            }
        )
        lead, _ = Lead.objects.get_or_create(
            email='linkedin_target@mock.com',
            defaults={
                'campaign': campaign,
                'first_name': 'LinkedIn',
                'last_name': 'Target',
                'status': 'uncontacted',
                'requires_human_review': True
            }
        )
        # Ensure lead is uncontacted for the test
        lead.status = 'uncontacted'
        lead.save()
        self.stdout.write(self.style.SUCCESS('1. Seeded Test Campaign and Lead (Status: uncontacted).'))

        # 2. Generate LinkedIn Task
        LinkedInTask.objects.filter(lead=lead).delete() # Clean old tests
        task = LinkedInTask.objects.create(
            lead=lead,
            campaign=campaign,
            task_type='connect',
            status='pending',
            instructions='Test Instructions: Connect and say hello.'
        )
        self.stdout.write(self.style.SUCCESS('2. Generated Pending LinkedIn Task.'))

        # 3. Simulate Frontend API Patch
        self.stdout.write(self.style.NOTICE('3. Simulating Frontend Operator clicking "Mark Complete"...'))
        client = APIClient()
        response = client.patch(f'/api/crm/linkedintasks/{task.id}/', {'status': 'completed'}, format='json')
        
        if response.status_code == 200:
            self.stdout.write(self.style.SUCCESS('   API PATCH Request Successful.'))
        else:
            self.stdout.write(self.style.ERROR(f'   API PATCH Request Failed: {response.status_code}'))
            return

        # 4. Assert CRM State Updates
        self.stdout.write(self.style.NOTICE('4. Validating CRM State Transitions...'))
        
        lead.refresh_from_db()
        if lead.status == 'in_sequence':
            self.stdout.write(self.style.SUCCESS('   SUCCESS: Lead pipeline status transitioned to "in_sequence".'))
        else:
            self.stdout.write(self.style.ERROR(f'   FAILED: Lead status is "{lead.status}", expected "in_sequence".'))
            
        audit = AuditLog.objects.filter(resource_type='LinkedInTask', resource_id=str(task.id)).first()
        if audit and audit.action == 'LinkedIn Manual Task Completed':
            self.stdout.write(self.style.SUCCESS('   SUCCESS: AuditLog generated to track manual human action.'))
        else:
            self.stdout.write(self.style.ERROR('   FAILED: AuditLog not found or action mismatch.'))

        self.stdout.write(self.style.SUCCESS('\nE2E LinkedIn Workflow Test Completed Successfully.'))
