from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0004_campaign_status_lead_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='value_proposition',
            field=models.TextField(blank=True, null=True),
        ),
    ]
