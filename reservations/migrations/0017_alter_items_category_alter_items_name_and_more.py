# Generated by Django 5.1.3 on 2024-12-17 05:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0016_delete_seat_remove_reservation_slot_index_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='items',
            name='category',
            field=models.CharField(choices=[(0, 'ホット'), (1, 'アイス'), (2, '軽食')], max_length=100, verbose_name='カテゴリ'),
        ),
        migrations.AlterField(
            model_name='items',
            name='name',
            field=models.CharField(max_length=200, verbose_name='品名'),
        ),
        migrations.AlterField(
            model_name='items',
            name='price',
            field=models.IntegerField(verbose_name='価格（税抜）'),
        ),
        migrations.AlterField(
            model_name='items',
            name='sort',
            field=models.IntegerField(verbose_name='ソート用'),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='hour',
            field=models.PositiveIntegerField(verbose_name='ご利用時間'),
        ),
    ]