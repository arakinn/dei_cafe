from django import forms
from django.forms import modelformset_factory
from .models import Reservation, ReservationItem, Items

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = [
            'slot_index', 'customer_name', 'phone_number', 'hour',
            'start', 'remark', 'is_preorder', 'is_eatin'
        ]
        labels = {
            'slot_index': 'お席',
            'customer_name': '代表者名',
            'phone_number': 'お電話番号',
            'hour': 'お時間（最大2時間）',
            'start': '開始時間',
            'remark': '備考欄',
            'is_preorder': '事前注文の有無',
            'is_eatin': 'イートイン/テイクアウト',
        }
        widgets = {
            'start': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

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
