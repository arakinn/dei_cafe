# Generated by Django 5.1.3 on 2024-12-13 02:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0013_alter_reservationitem_quantity_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Seat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.IntegerField(unique=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='reservation',
            name='slot_index',
        ),
        migrations.AddField(
            model_name='reservation',
            name='seats',
            field=models.ManyToManyField(to='reservations.seat'),
        ),
    ]
