from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('openedx_lti_tool_plugin', '0012_alter_ltiactivitylineitem_lineitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='ltitoolconfiguration',
            name='grade_passback_mode',
            field=models.CharField(
                choices=[
                    ('coupled', 'Coupled — one column per placement (Canvas, Blackboard, default)'),
                    ('per_problem', 'Per-problem — one column per problem (Moodle only)'),
                ],
                default='coupled',
                help_text=(
                    'How AGS scores are sent to this platform: "Coupled" (default) posts one '
                    'aggregate score per placement and works everywhere; "Per-problem" also '
                    'creates one column per problem and is Moodle-only.'
                ),
                max_length=20,
                verbose_name='Grade Passback Mode',
            ),
        ),
    ]
