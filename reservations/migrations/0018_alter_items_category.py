# Generated by Django 5.1.3 on 2024-12-17 06:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0017_alter_items_category_alter_items_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='items',
            name='category',
            field=models.CharField(max_length=100, verbose_name='カテゴリ'),
        ),
    ]
