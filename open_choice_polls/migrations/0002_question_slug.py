# Generated by Django 3.0.2 on 2020-02-01 20:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('open_choice_polls', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='slug',
            field=models.SlugField(blank=True, editable=False),
        ),
    ]
