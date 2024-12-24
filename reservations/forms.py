from django import forms
from django.contrib.auth.models import User
from .models import Reservation, ReservationItem, Items, Comment
from django.core.exceptions import ValidationError
from django.utils.timezone import make_aware
from datetime import timedelta, datetime, date
from django.db import models
import re

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
        phone_number = cleaned_data.get('phone_number')  # 電話番号

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
            ).aggregate(models.Sum('seat_count'))['seat_count__sum'] or 0

            remaining_seats = 8 - total_reserved_seats  # 最大8席

            # 席数が残り席数を超えていないかチェック
            if seat_count > remaining_seats:
                self.add_error('seat_count', f"この時間帯の残り席数は {remaining_seats} 席です。席数を減らしてください。")
        
            # 終了時間 (end) が17:00を超えている場合にエラーを追加
            if end_time.hour > 17:  # 終了時間が17時を超える場合
                self.add_error('hour', 'ご利用終了時間は17時までに収めてください。')

        # 注文の動的チェック
        item_fields = [field for field in self.data if field.startswith('item_')]
        total_quantity = sum(int(self.data.get(field, 0)) for field in item_fields)

        # 事前注文が選択されているのに注文が0の場合
        if is_preorder == 1 and total_quantity == 0:
            self.add_error('is_preorder', '事前注文が選ばれている場合、注文を1つ以上選択してください。')

        # お店で注文が選択されているのに注文が1以上の場合
        if is_preorder == 2 and total_quantity > 0:
            self.add_error('is_preorder', 'お店で注文の場合、注文は必要ありません。')

        # 電話番号が数字以外を含む場合にエラーを出す
        if phone_number and not re.fullmatch(r'[0-9]+', phone_number):
            self.add_error('phone_number', '電話番号は半角数字のみを入力してください。')
        
        # 商品の注文期限チェック
        if is_preorder == 1 and start_time:  # 事前注文で予約日がある場合のみチェック
            reservation_date = start_time.date()  # `start` は日時なので日付部分を取得

            for field_name, value in self.data.items():
                if field_name.startswith('item_'):
                    try:
                        item_id = int(field_name.split('_')[1])
                        item = Items.objects.get(id=item_id)
                        quantity = int(value) if value else 0

                        # 注文期限が設定されていて、予約日が注文期限を超えていた場合エラー
                        if quantity > 0 and item.order_deadline and reservation_date > item.order_deadline:
                            self.add_error(None, f"{item.name} の注文期限は {item.order_deadline} までです。")
                    except (ValueError, Items.DoesNotExist):
                        continue

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


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'}),
        help_text="半角英数字と記号のみ使用可能"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password 確認用'}),
        help_text="確認のため、もう一度パスワードを入力してください"
    )

    class Meta:
        model = User
        fields = ['username']  # username のみでフォームを作成

    def clean_username(self):
        username = self.cleaned_data.get("username")

        # 半角英数字と記号のみ許可
        if not re.fullmatch(r'[a-zA-Z0-9!@.+-_]+', username):

            raise forms.ValidationError("ユーザー名は半角英数字と一部の記号のみ使用可能です。")
        
        return username

    def clean_password(self):
        password = self.cleaned_data.get("password")

        # 半角英数字と記号のみ許可
        if not re.fullmatch(r'[a-zA-Z0-9!@.+-_]+', password):
            raise forms.ValidationError("パスワードは半角英数字と一部の記号のみ使用可能です。")
        
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        # パスワード一致チェック
        if password and password_confirm and password != password_confirm:
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

        #店舗側は予約時間制限なし
#       self.fields['hour'].widget = forms.Select(choices=((0, "0時間"), (1, "1時間"), (2, "2時間")))

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
        phone_number = cleaned_data.get('phone_number')  # 電話番号

        # テイクアウトが選択されているのに時間が0以外の場合エラーを出す
        if is_eatin == 2 and hour not in (None, 0):  # hour が None または 0 以外の場合エラー
            self.add_error('hour', 'テイクアウトの場合、ご利用時間は0時間にしてください。')

        # イートインの場合に時間が0ではエラーを出す
        if is_eatin == 1 and (hour is None or hour == 0):  # hour が None または 0 の場合エラー
            self.add_error('hour', 'イートインの場合、ご利用時間は0時間以外にしてください。')

        # 開始時間が取得できた場合に席数を確認
        if start_time and seat_count is not None:
            # 終了時間を計算
            end_time = start_time + timedelta(hours=hour or 0)  # hour が None の場合 0 を使用

            # 同時間帯の予約済み席数を計算
            total_reserved_seats = Reservation.objects.filter(
                start__lt=end_time,
                end__gt=start_time
            ).aggregate(models.Sum('seat_count'))['seat_count__sum'] or 0

            remaining_seats = 8 - total_reserved_seats  # 最大8席

            # 席数が残り席数を超えていないかチェック
            if seat_count > remaining_seats:
                self.add_error('seat_count', f"この時間帯の残り席数は {remaining_seats} 席です。席数を減らしてください。")
        
            # 終了時間 (end) が17:00を超えている場合にエラーを追加
            if end_time.hour > 17:  # 終了時間が17時を超える場合
                self.add_error('hour', 'ご利用終了時間は17時までに収めてください。')

        # 注文の動的チェック
        item_fields = [field for field in self.data if field.startswith('item_')]
        total_quantity = 0

        for field in item_fields:
            field_value = self.data.get(field, '0').strip()  # 空文字列は '0' として処理
            if field_value:
                try:
                    total_quantity += int(field_value)
                except ValueError:
                    self.add_error(field, "数量には数値を入力してください。")

        # 事前注文が選択されているのに注文が0の場合
        if is_preorder == 1 and total_quantity == 0:
            self.add_error('is_preorder', '事前注文が選ばれている場合、注文を1つ以上選択してください。')

        # お店で注文が選択されているのに注文が1以上の場合
        if is_preorder == 2 and total_quantity > 0:
            self.add_error('is_preorder', 'お店で注文の場合、注文は必要ありません。')

        # 電話番号が数字以外を含む場合にエラーを出す
        if phone_number and not re.fullmatch(r'[0-9]+', phone_number):
            self.add_error('phone_number', '電話番号は半角数字のみを入力してください。')

        # 商品の注文期限チェック
        if is_preorder == 1 and start_time:  # 事前注文で予約日がある場合のみチェック
            reservation_date = start_time.date()  # `start` は日時なので日付部分を取得

            for field_name, value in self.data.items():
                if field_name.startswith('item_'):
                    try:
                        item_id = int(field_name.split('_')[1])
                        item = Items.objects.get(id=item_id)
                        quantity = int(value) if value else 0

                        # 注文期限が設定されていて、予約日が注文期限を超えていた場合エラー
                        if quantity > 0 and item.order_deadline and reservation_date > item.order_deadline:
                            self.add_error(None, f"{item.name} の注文期限は {item.order_deadline} までです。")
                    except (ValueError, Items.DoesNotExist):
                        continue
                    
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
    CATEGORY_CHOICES = [
        ('軽食', '軽食'),
        ('ホット', 'ホット'),
        ('アイス', 'アイス'),
    ]

    # category をプルダウン形式で定義
    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        widget=forms.Select,
        label="カテゴリ",
    )

    class Meta:
        model = Items
        fields = ['name', 'price', 'category', 'sort', 'order_deadline']

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': 'お店からのお知らせを入力してください'}),
        }
        labels = {
            'content': 'お知らせ内容',
        }