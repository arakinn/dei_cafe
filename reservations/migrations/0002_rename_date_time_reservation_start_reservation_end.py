# Generated by Django 5.1.3 on 2024-12-09 02:17

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='reservation',
            old_name='date_time',
            new_name='start',
        ),
        migrations.AddField(
            model_name='reservation',
            name='end',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]