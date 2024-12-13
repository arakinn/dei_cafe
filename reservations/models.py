
import datetime
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone

# Create your models here.

class Seat(models.Model):
    number = models.IntegerField(unique=True)  # 座席番号

    def __str__(self):
        return f"Seat {self.number}"


class Items(models.Model):
    category = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    price = models.IntegerField()
    sort = models.IntegerField()

    def __str__(self):
        return self.name

class Reservation(models.Model):
    RESERVATION_SLOT = ((1, '1席'),(2, '2席'), (3, '3席'), (4, '4席'), (5, '5席'), (6, '6席'), (7, '7席'), (8, '8席'))
    slot_index = models.IntegerField(choices=RESERVATION_SLOT, verbose_name="お席")
    customer_name = models.CharField(max_length=60, verbose_name="代表者名")
    phone_number = models.CharField(max_length=15, verbose_name="お電話番号")
    hour = models.PositiveIntegerField(verbose_name="お時間（最大2時間）")
    start = models.DateTimeField(verbose_name="開始時間")
    end = models.DateTimeField(verbose_name="終了時間", null=True, blank=True)
    remark = models.TextField(max_length=200, verbose_name="備考欄", null=True, blank=True)
    RESERVATION_IS_PREORDER = ((1, '事前注文'), (2, 'お店で注文'))
    is_preorder = models.IntegerField(choices=RESERVATION_IS_PREORDER, verbose_name="事前注文の有無")
    RESERVATION_IS_EATIN = ((1, 'イートイン'), (2, 'テイクアウト'))
    is_eatin = models.IntegerField(choices=RESERVATION_IS_EATIN, verbose_name="イートイン/テイクアウト")
    menu_items = models.ManyToManyField(Items, through='ReservationItem', verbose_name="注文メニュー")

    def save(self, *args, **kwargs):
        if self.start and self.hour:
            # 終了時間を計算
            self.end = self.start + datetime.timedelta(hours=self.hour)
        super().save(*args, **kwargs)

class ReservationItem(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(Items, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.item.name} x {self.quantity}"