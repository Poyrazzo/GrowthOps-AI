import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Campaign',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('target_sector', models.CharField(max_length=255)),
                ('target_country', models.CharField(max_length=100)),
                ('target_persona', models.CharField(max_length=255)),
                ('value_proposition', models.TextField()),
                ('lead_magnet', models.CharField(blank=True, max_length=255, null=True)),
                ('outreach_channel', models.CharField(choices=[('email', 'Email'), ('linkedin', 'LinkedIn')], max_length=50)),
                ('success_metric', models.CharField(blank=True, max_length=255, null=True)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('domain', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('linkedin_url', models.URLField(blank=True, null=True)),
                ('sector', models.CharField(blank=True, max_length=255, null=True)),
                ('size', models.CharField(blank=True, max_length=100, null=True)),
                ('location', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='LeadSource',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=500, unique=True)),
                ('source_type', models.CharField(choices=[('static', 'Static Website'), ('dynamic', 'Dynamic Website'), ('linkedin', 'LinkedIn'), ('directory', 'Directory')], max_length=50)),
                ('sector', models.CharField(max_length=255)),
                ('expected_data_fields', models.JSONField(blank=True, default=dict)),
                ('access_rules', models.TextField(blank=True)),
                ('priority_score', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Lead',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField(blank=True, max_length=254, null=True, unique=True)),
                ('first_name', models.CharField(blank=True, max_length=150, null=True)),
                ('last_name', models.CharField(blank=True, max_length=150, null=True)),
                ('title', models.CharField(blank=True, max_length=255, null=True)),
                ('linkedin_url', models.URLField(blank=True, null=True)),
                ('persona', models.CharField(blank=True, max_length=255, null=True)),
                ('department', models.CharField(blank=True, max_length=150, null=True)),
                ('lead_score', models.IntegerField(default=0)),
                ('score_reason', models.TextField(blank=True)),
                ('recommended_message_angle', models.TextField(blank=True)),
                ('requires_human_review', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('campaign', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='leads', to='crm.campaign')),
                ('company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='leads', to='crm.company')),
                ('source', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='leads', to='crm.leadsource')),
            ],
        ),
        migrations.AddConstraint(
            model_name='lead',
            constraint=models.UniqueConstraint(fields=('email', 'linkedin_url'), name='unique_lead'),
        ),
    ]
