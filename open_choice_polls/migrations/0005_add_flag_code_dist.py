# Generated by Django 2.2.10 on 2020-02-15 17:24

from django.db import migrations, models
import django.db.models.functions.text


class Migration(migrations.Migration):

    dependencies = [
        ('open_choice_polls', '0004_add_anon_voter'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='choice',
            options={'ordering': [django.db.models.functions.text.Lower('choice_text')], 'verbose_name': 'choice', 'verbose_name_plural': 'choices'},
        ),
        migrations.AlterModelOptions(
            name='question',
            options={'get_latest_by': 'created', 'ordering': ('-created',)},
        ),
        migrations.AddField(
            model_name='voter',
            name='enrollment_code_is_distributed',
            field=models.BooleanField(default=False, verbose_name='Is Distributed?'),
        ),
    ]
