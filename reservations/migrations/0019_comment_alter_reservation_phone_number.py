# Generated by Django 5.1.3 on 2024-12-20 11:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0018_alter_items_category'),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(max_length=500, verbose_name='コメント内容')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日')),
            ],
        ),
        migrations.AlterField(
            model_name='reservation',
            name='phone_number',
            field=models.CharField(max_length=15, verbose_name='お電話番号（ハイフンなし）'),
        ),
    ]
