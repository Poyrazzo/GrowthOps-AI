from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0007_activity_leadmagnetsubmission_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='profile_url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name='lead',
            constraint=models.UniqueConstraint(
                condition=Q(profile_url__isnull=False) & ~Q(profile_url=''),
                fields=('profile_url',),
                name='unique_lead_profile_url',
            ),
        ),
    ]
