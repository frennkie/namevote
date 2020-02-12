# Generated by Django 2.2.9 on 2020-02-02 18:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('open_choice_polls', '0002_question_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='choice_validation_hint',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='question',
            name='choice_validation_regex',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='question',
            name='description',
            field=models.TextField(blank=True, verbose_name='Description (with basic markdown support)'),
        ),
    ]