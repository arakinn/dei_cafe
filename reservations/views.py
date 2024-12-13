import datetime
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
from .models import Reservation
from django.views import generic
from django.conf import settings
from .forms import ReservationForm
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.shortcuts import redirect, get_object_or_404

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

        # クエリパラメータ 'phonenumber' を取得
        phonenumber = self.request.GET.get('phonenumber', '123456789')  # デフォルト値を '123456789' に設定
        context['phonenumber'] = phonenumber  # テンプレートに渡す

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
        print("フォームは有効です:", form.is_valid())
        reservation = form.save(commit=False)
    
        # 予約の保存
        reservation.save()

        # メニュー項目の保存
        form.save_menus(reservation)

        # 終了時間を計算
        reservation.end = reservation.start + timedelta(hours=reservation.hour)

       # 同じ時間帯、同じ席がすでに予約されていないか確認
        print(f"予約の席番号: {reservation.slot_index}")  # 席番号が正しいか確認
        print(f"予約の開始: {reservation.start}, 終了: {reservation.end}")
        conflicting_reservation = Reservation.objects.filter(
            start__lt=reservation.end,  # 現在の予約の終了時刻より早く開始する予約
            end__gt=reservation.start,  # 現在の予約の開始時刻より遅く終了する予約
            slot_index=reservation.slot_index  # 同じ席番号
        ).exclude(id=reservation.id)  # 自分自身を除外

        print(f"チェック対象の予約: {list(conflicting_reservation)}")  # デバッグ用に出力
        if conflicting_reservation.exists():
            form.add_error(None, "この時間帯、この席はすでに予約されています。他の席を選択してください。")
            print("重複する予約:", conflicting_reservation)
            return self.form_invalid(form)

        # 予約が重複していない場合は保存
        reservation.save()

        # 予約完了ページにリダイレクト
        print(f"予約完了ページにリダイレクト: reservation_id={reservation.id}")
        return redirect(reverse('complete') + f'?reservation_id={reservation.id}')


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