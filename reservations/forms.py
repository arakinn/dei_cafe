from django import forms
from django.contrib.auth.models import User
from .models import Reservation, ReservationItem, Items

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