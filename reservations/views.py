import datetime
import math
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from typing import Any
from django.db.models import Q
from django.shortcuts import render
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from .models import Reservation, ReservationItem, Items
from django.views import generic
from django.conf import settings
from .forms import ReservationForm, ReservationItemForm
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404


# Create your views here.


class LoginView(LoginView):
    form_class = AuthenticationForm
    template_name = 'reservations/login.html'

class LogoutView(LogoutView):
    template_name = 'logout.html'

class MenuUserView(TemplateView):
    template_name = 'reservations/menu_user.html'

class ReservationListView(TemplateView):
    template_name = 'reservations/reservation_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # クエリパラメータ 'phone_number' を取得
        phone_number = self.request.GET.get('phone_number', '123456789')  # デフォルト値を '123456789' に設定
        context['phone_number'] = phone_number  # テンプレートに渡す

        return context

class CalendarView(generic.TemplateView):
    template_name = 'reservations/calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = datetime.now().date()  # 今日の日付を取得

        # URLから年・月・日を取得し、基準日を設定
        year = self.kwargs.get('year')
        month = self.kwargs.get('month')
        day = self.kwargs.get('day')
        if year and month and day:
            base_date = datetime(year=int(year), month=int(month), day=int(day)).date()
        else:
            base_date = today

        days = [base_date + timedelta(days=i) for i in range(7)]
        start_day = days[0]
        end_day = days[-1]

        calendar = {}
        max_slots = 8  # 1時間あたりの予約枠数
        for hour in range(10, 17):  # 営業時間
            row = {}
            for day in days:
                row[day] = [True] * max_slots  # 各日付・時間帯の枠を初期化
            calendar[hour] = row

        start_time = datetime.combine(start_day, datetime.min.time().replace(hour=10))
        end_time = datetime.combine(end_day, datetime.min.time().replace(hour=17))
        start_time = make_aware(start_time)
        end_time = make_aware(end_time)

        for schedule in Reservation.objects.exclude(Q(start__gt=end_time) | Q(end__lt=start_time)):
            local_dt = timezone.localtime(schedule.start)
            booking_date = local_dt.date()
            booking_hour = local_dt.hour
            slot_index = schedule.slot_index - 1  # インデックス調整（1から始まるため）

            if booking_hour in calendar and booking_date in calendar[booking_hour]:
                if 0 <= slot_index < max_slots:
                    calendar[booking_hour][booking_date][slot_index] = False

        availability = {}
        for hour, days_slots in calendar.items():
            availability[hour] = {}
            for day, slots in days_slots.items():
                availability[hour][day] = any(slots)  # 空きがあればTrue, 全て埋まっていればFalse

        context['availability'] = availability
        context['days'] = days
        context['start_day'] = start_day
        context['end_day'] = end_day
        context['before'] = days[0] - timedelta(days=7)
        context['next'] = days[-1] + timedelta(days=1)
        context['today'] = today

        return context

'''
from .models import Reservation

class WeeklyView(ListView):
    model = Reservation  # モデルの指定
    template_name = 'reservations/weekly.html'  # 使用するテンプレート
    context_object_name = 'reservations'  # コンテキスト内でのオブジェクト名

    def get_queryset(self):
        # クエリパラメータ 'name' を取得
        name = self.request.GET.get('name', None)  # デフォルトはNone
        queryset = super().get_queryset()

        # 'name'が存在すれば、予約情報をフィルタリング
        if name:
            queryset = queryset.filter(customer_name__icontains=name)  # フィルタリング例

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # クエリパラメータ 'name' をコンテキストに追加
        name = self.request.GET.get('name', 'ゲスト')  # デフォルト値は'ゲスト'
        context['name'] = name
        return context
'''
class ReservationView(CreateView):
    template_name = 'reservations/reservation_form.html'
    form_class = ReservationForm
    model = Reservation

    def get_initial(self):
        initial = super().get_initial()

        # URLパラメータから予約日時を取得
        year = self.kwargs.get('year')
        month = self.kwargs.get('month')
        day = self.kwargs.get('day')
        hour = self.kwargs.get('hour')

        # 初期値として予約日時を設定
        if year and month and day and hour:
            start_time = datetime(year=int(year), month=int(month), day=int(day), hour=int(hour))
            initial['start'] = make_aware(start_time)  # タイムゾーンを適用

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # フォームを取得
        form = self.get_form()

        # 'item_' で始まるフィールドを抽出
        items_fields = [field for field in form if field.name.startswith('item_')]
        
        # 'item_' 以外のフィールドを抽出
        other_fields = [field for field in form if not field.name.startswith('item_')]
        
        # コンテキストに渡す
        context['form'] = form
        context['items_fields'] = items_fields
        context['other_fields'] = other_fields
        
        return context

    def form_valid(self, form):
        reservation = form.save(commit=False)  # 一時的に保存（まだDBには書き込まない）

        # 終了時間を計算
        reservation.end = reservation.start + timedelta(hours=reservation.hour)

        # 同じ時間帯、同じ席の予約がないか確認
        conflicting_reservations = Reservation.objects.filter(
            start__lt=reservation.end,  # 現在の予約の終了時刻より早く開始する予約
            end__gt=reservation.start,  # 現在の予約の開始時刻より遅く終了する予約
            slot_index=reservation.slot_index  # 同じ席番号
        ).exclude(id=reservation.id)  # 自分自身を除外

        if conflicting_reservations.exists():
            # フォームにエラーを追加
            form.add_error(None, "この時間帯、この席はすでに予約されています。他の席を選択してください。")
            return self.form_invalid(form)  # エラー時は保存せず、フォームを再表示

        # 予約情報を保存
        reservation.save()

        # 注文メニュー (ReservationItem) を保存
        for field_name, field_value in self.request.POST.items():
            if field_name.startswith('item_'):
                try:
                    item_id = field_name.split('_')[1]  # item_ の後に続くID
                    quantity = int(field_value)

                    if quantity > 0:  # quantity が 0 より大きい場合のみ保存
                        # ReservationItem を作成
                        item = Items.objects.get(id=item_id)
                        reservation_item = ReservationItem(
                            reservation=reservation,
                            item=item,
                            quantity=quantity
                        )
                        reservation_item.save()

                except (ValueError, IndexError, Items.DoesNotExist):
                    continue  # エラーがあれば無視して次へ進む

    # 予約完了ページにリダイレクト
        return redirect(reverse('complete') + f'?reservation_id={reservation.id}')

"""
class ReservationCompleteView(TemplateView):
    template_name = 'reservations/reservation_complete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # GETパラメータから予約IDを取得
        reservation_id = self.request.GET.get('reservation_id')
        if reservation_id:
            try:
                reservation = Reservation.objects.get(id=reservation_id)
                context['reservation'] = reservation
            except Reservation.DoesNotExist:
                context['reservation'] = None
        else:
            context['reservation'] = None

        return context
"""

class ReservationCompleteView(TemplateView):
    def get(self, request, *args, **kwargs):
        reservation_id = request.GET.get("reservation_id")
        reservation = get_object_or_404(Reservation, id=reservation_id)
        reservation_items = ReservationItem.objects.filter(reservation=reservation)

        # 計算処理
        reservation_details = []
        total_excl_tax = 0

        for item in reservation_items:
            item_total = item.item.price * item.quantity  # 小計を計算
            total_excl_tax += item_total
            reservation_details.append({
                "name": item.item.name,
                "quantity": item.quantity,
                "price": item.item.price,
                "total": item_total,
            })

        tax_amount = total_excl_tax * 0.1  # 消費税額
        discount_amount = (total_excl_tax + tax_amount) * 0.1  # 割引額
        discount_amount = int(discount_amount)  # 小数点以下を切り捨て
        total_incl_tax = total_excl_tax + tax_amount - discount_amount

        context = {
            "reservation": reservation,
            "reservation_details": reservation_details,
            "total_excl_tax": total_excl_tax,
            "tax_amount": tax_amount,
            "discount_amount": discount_amount,
            "total_incl_tax": total_incl_tax,
        }
        return render(request, "reservations/reservation_complete.html", context)