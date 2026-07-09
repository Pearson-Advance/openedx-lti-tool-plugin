from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('openedx_lti_tool_plugin', '0013_ltitoolconfiguration_grade_passback_mode'),
    ]

    operations = [
        migrations.AddField(
            model_name='ltiactivitylineitem',
            name='resource_link_id',
            field=models.CharField(
                blank=True,
                default='',
                help_text='LTI resource link id — the specific platform activity/placement.',
                max_length=255,
            ),
        ),
        migrations.AlterUniqueTogether(
            name='ltiactivitylineitem',
            unique_together={('platform_id', 'context_id', 'resource_link_id', 'problem_id')},
        ),
    ]
