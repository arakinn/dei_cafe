# Generated by Django 5.1.3 on 2024-12-23 11:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0021_items_order_deadline'),
    ]

    operations = [
        migrations.AlterField(
            model_name='items',
            name='order_deadline',
            field=models.DateField(blank=True, null=True, verbose_name='注文期限'),
        ),
    ]