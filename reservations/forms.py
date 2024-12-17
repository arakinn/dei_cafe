from django import forms
from django.contrib.auth.models import User
from .models import Reservation, ReservationItem, Items
from django.core.exceptions import ValidationError
from django.utils.timezone import make_aware
from datetime import timedelta, datetime
from django.db import models

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = [
            'seat_count', 'customer_name', 'phone_number', 'hour', 'start', 'remark', 'is_preorder', 'is_eatin'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['hour'].widget = forms.Select(choices=((0, "0時間"), (1, "1時間"), (2, "2時間")))

        # メニュー項目を動的に追加
        items = Items.objects.all().order_by('sort')  # メニューを並べ替え
        for item in items:
            # 予約に関連付けられたアイテムの数量を取得
            quantity = 0
            if self.instance.pk:  # 予約が既に存在する場合
                reservation_items = self.instance.items.filter(item=item)
                if reservation_items.exists():
                    quantity = reservation_items.first().quantity

            # フォームにフィールドを追加し、初期値に数量を設定
            self.fields[f'item_{item.id}'] = forms.IntegerField(
                label=f'{item.name} ({item.price}円)',
                required=False,
                initial=quantity,  # 初期値に数量を設定
                widget=forms.NumberInput(attrs={'min': '0', 'step': '1'})
            )
    
     
    def clean(self):
        cleaned_data = super().clean()
        is_eatin = cleaned_data.get('is_eatin')  # イートイン/テイクアウトの選択肢
        hour = cleaned_data.get('hour')  # 利用時間
        seat_count = cleaned_data.get('seat_count')  # 予約席数
        start_time = cleaned_data.get('start')  # 開始時間
        is_preorder = cleaned_data.get('is_preorder')  # 事前注文の有無

        # テイクアウトが選択されているのに時間が0以外の場合エラーを出す
        if is_eatin == 2 and hour != 0:  # テイクアウトの場合は時間を0時間に
            self.add_error('hour', 'テイクアウトの場合、ご利用時間は0時間にしてください。')

        # イートインの場合に時間が0ではエラーを出す
        if is_eatin == 1 and hour == 0:  # イートインの選択肢が '1' で時間が0の場合
            self.add_error('hour', 'イートインの場合、ご利用時間は0時間以外にしてください。')

        # 開始時間が取得できた場合に席数を確認
        if start_time and seat_count is not None:
            # 終了時間を計算
            end_time = start_time + timedelta(hours=hour)

            # 同時間帯の予約済み席数を計算
            total_reserved_seats = Reservation.objects.filter(
                start__lt=end_time,
                end__gt=start_time
            ).aggregate(models.Sum('seat_count'))['seat_count__sum'] or 0  # ここで models.Sum を使用

            remaining_seats = 8 - total_reserved_seats  # 最大8席

            # 席数が残り席数を超えていないかチェック
            if seat_count > remaining_seats:
                self.add_error(None, f"この時間帯の残り席数は {remaining_seats} 席です。席数を減らしてください。")
        
            # 終了時間 (end) が17:00を超えている場合にエラーを追加
            if end_time.hour > 17:  # 終了時間が17時を超える場合
                self.add_error('hour', 'ご利用時間は17時までに収めてください。')

        # 事前注文の場合に注文が0の時エラー
        if is_preorder == 1:  # 事前注文が選ばれている場合
            # 注文数が全て0の時エラーを出す
            items = cleaned_data.get('items')
            if items and all(item.quantity == 0 for item in items):  # itemsがNoneでないことを確認
                self.add_error('items', '事前注文が選ばれている場合、注文を1つ以上選択してください。')

        # お店で注文の場合に注文が1以上の時エラー
        if is_preorder == 2:  # お店で注文が選ばれている場合
            # 注文数が1以上の時エラーを出す
            items = cleaned_data.get('items')
            if items and any(item.quantity > 0 for item in items):  # itemsがNoneでないことを確認
                self.add_error('items', 'お店で注文の場合、注文は必要ありません。')

        return cleaned_data



    def save(self, commit=True):
        reservation = super().save(commit=False)

        if commit:
            reservation.save()
            self.save_menus(reservation)

        return reservation

    def save_menus(self, reservation):
        # 予約に関連付けられた注文を保存
        for field_name, field_value in self.cleaned_data.items():
            if field_name.startswith("item_"):
                item_id = int(field_name.split('_')[1])
                item = Items.objects.get(id=item_id)
                quantity = field_value
                if quantity > 0:
                    ReservationItem.objects.create(
                        reservation=reservation,
                        item=item,
                        quantity=quantity
                    )



class ReservationItemForm(forms.ModelForm):
    class Meta:
        model = ReservationItem
        fields = ['item', 'quantity']

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))

    class Meta:
        model = User
        fields = ['username']  # username のみでフォームを作成

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password != password_confirm:
            raise forms.ValidationError("パスワードが一致しません。")
        return cleaned_data

class ShopReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = [
            'seat_count', 'customer_name', 'phone_number', 'hour', 'start', 'remark', 'is_preorder', 'is_eatin'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # メニュー項目を動的に追加
        items = Items.objects.all().order_by('sort')  # メニューを並べ替え
        for item in items:
            # 予約に関連付けられたアイテムの数量を取得
            quantity = 0
            if self.instance.pk:  # 予約が既に存在する場合
                reservation_items = self.instance.items.filter(item=item)
                if reservation_items.exists():
                    quantity = reservation_items.first().quantity

            # フォームにフィールドを追加し、初期値に数量を設定
            self.fields[f'item_{item.id}'] = forms.IntegerField(
                label=f'{item.name} ({item.price}円)',
                required=False,
                initial=quantity,  # 初期値に数量を設定
                widget=forms.NumberInput(attrs={'min': '0', 'step': '1'})
            )

    def clean(self):
        cleaned_data = super().clean()
        is_eatin = cleaned_data.get('is_eatin')  # イートイン/テイクアウトの選択肢
        hour = cleaned_data.get('hour')  # 利用時間
        seat_count = cleaned_data.get('seat_count')  # 予約席数
        start_time = cleaned_data.get('start')  # 開始時間

        # テイクアウトが選択されているのに時間が0以外の場合エラーを出す
        if is_eatin == 2 and hour != 0:  # テイクアウトの場合は時間を0時間に
            self.add_error('hour', 'テイクアウトの場合、ご利用時間は0時間にしてください。')

        # イートインの場合に時間が0ではエラーを出す
        if is_eatin == 1 and hour == 0:  # イートインの選択肢が '1' で時間が0の場合
            self.add_error('hour', 'イートインの場合、ご利用時間は0時間以外にしてください。')

        # 開始時間が取得できた場合に席数を確認
        if start_time and seat_count is not None:
            # 終了時間を計算
            end_time = start_time + timedelta(hours=hour)

            # 同時間帯の予約済み席数を計算
            total_reserved_seats = Reservation.objects.filter(
                start__lt=end_time,
                end__gt=start_time
            ).aggregate(models.Sum('seat_count'))['seat_count__sum'] or 0  # ここで models.Sum を使用

            remaining_seats = 8 - total_reserved_seats  # 最大8席

            # 席数が残り席数を超えていないかチェック
            if seat_count > remaining_seats:
                self.add_error(None, f"この時間帯の残り席数は {remaining_seats} 席です。席数を減らしてください。")
            
            # 終了時間 (end) が17:00を超えている場合にエラーを追加
            if start_time:
                end_time = start_time + timedelta(hours=hour)
                if end_time.hour > 17:  # 終了時間が17時を超える場合
                    self.add_error('hour', 'ご利用時間は17時までに収めてください。')

        return cleaned_data
    
    def save(self, commit=True):
        reservation = super().save(commit=False)

        if commit:
            reservation.save()
            self.save_menus(reservation)

        return reservation

    def save_menus(self, reservation):
        # 予約に関連付けられた注文を保存
        for field_name, field_value in self.cleaned_data.items():
            if field_name.startswith("item_"):
                item_id = int(field_name.split('_')[1])
                item = Items.objects.get(id=item_id)
                quantity = field_value
                if quantity > 0:
                    ReservationItem.objects.create(
                        reservation=reservation,
                        item=item,
                        quantity=quantity
                    )

class ItemForm(forms.ModelForm):
    class Meta:
        model = Items
        fields = ['name', 'price', 'category', 'sort']