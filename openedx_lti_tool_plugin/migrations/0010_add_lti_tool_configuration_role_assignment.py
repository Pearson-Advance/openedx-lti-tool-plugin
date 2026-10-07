from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('openedx_lti_tool_plugin', '0009_update_lti_profile'),
    ]

    operations = [
        migrations.AddField(
            model_name='ltitoolconfiguration',
            name='enable_role_assignment',
            field=models.BooleanField(default=False, help_text='When enabled, the LTI roles claim from a launch is translated into an Open edX course role for this tool, using the role mapping below. Disabled by default: existing tools keep their current behavior (every launched user is enrolled as a Student).', verbose_name='Enable role assignment'),
        ),
        migrations.AddField(
            model_name='ltitoolconfiguration',
            name='role_mapping',
            field=models.JSONField(blank=True, default=dict, help_text='\n        <p>Maps LTI role URIs to Open edX course roles. Leave empty to use the\n        plugin default mapping.</p>\n        <p>Keys are LTI role URIs, values are one of\n        <code>"instructor"</code>, <code>"staff"</code> or\n        <code>"student"</code>. Only course-context roles are honored; system\n        and institution roles are ignored. Example:</p>\n        <pre>{\n    "http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor": "instructor",\n    "http://purl.imsglobal.org/vocab/lis/v2/membership#Administrator": "staff"\n}</pre>\n        ', verbose_name='Role mapping'),
        ),
    ]
