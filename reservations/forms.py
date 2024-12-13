from django import forms
from django.forms import modelformset_factory
from .models import Reservation, ReservationItem, Items

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
        if hour <= 0 or hour > 2:
            raise forms.ValidationError('予約時間は1〜2時間の範囲で選択してください。')
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

class ReservationItemForm(forms.ModelForm):
    class Meta:
        model = ReservationItem
        fields = ['item', 'quantity']