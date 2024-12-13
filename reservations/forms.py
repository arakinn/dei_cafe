from django import forms
from django.contrib.auth.models import User
from .models import Reservation, ReservationItem, Items
"""
class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = [
            'customer_name', 'phone_number', 'hour', 'start', 'seat_count',
            'remark', 'is_preorder', 'is_eatin'
        ]
        labels = {
            'seat_count': '席数（最大8席）',
            # その他のラベルは変更なし
        }
        widgets = {
            'start': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

    def clean_seat_count(self):
        seat_count = self.cleaned_data.get('seat_count')
        if seat_count is None or seat_count <= 0 or seat_count > 8:
            raise forms.ValidationError("席数は1〜8の範囲で指定してください。")
        return seat_count

    def clean_hour(self):
        hour = self.cleaned_data.get('hour')
        if hour is None:
            raise forms.ValidationError('予約時間を入力してください。')
        if hour <= -1 or hour > 2:
            raise forms.ValidationError('予約時間は0〜2時間の範囲で選択してください。')
        return hour

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # すべてのメニューを取得し、数量を入力するフィールドを動的に追加
        items = Items.objects.all().order_by('sort')  # メニューを並べ替え
        for item in items:
            self.fields[f'item_{item.id}'] = forms.IntegerField(
                label=f'{item.name} ({item.price}円)',  # メニュー名と価格
                required=False,
                initial=0,
                widget=forms.NumberInput(attrs={'min': '0', 'step': '1'}),
            )

    def clean(self):
        cleaned_data = super().clean()
        # メニュー選択の必須条件を削除
        return cleaned_data

    def save(self, commit=True):
        reservation = super().save(commit=False)

        if commit:
            reservation.save()
            self.save_menus(reservation)

        return reservation

    def save_menus(self, reservation):
        items = []  # メニューアイテムのリストを保存
        for field in self.cleaned_data:
            if field.startswith("item_"):  # メニューアイテムのフィールド
                item_id = int(field.split("_")[1])
                item = Items.objects.get(id=item_id)
                quantity = self.cleaned_data[field]
                if quantity > 0:  # 数量が0以上の場合のみ保存
                    ReservationItem.objects.create(
                        reservation=reservation,
                        item=item,
                        quantity=quantity
                    )
        return items
"""

class ReservationForm(forms.ModelForm):
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