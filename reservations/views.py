import datetime
import math
from django.db.models import Sum
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from typing import Any
from django.shortcuts import render
from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from django.utils.timezone import now
from .models import Reservation, ReservationItem, Items
from django.views import generic
from django.conf import settings
from .forms import ReservationForm, ReservationItemForm, ShopReservationForm
from django.core.exceptions import ValidationError
from django.urls import reverse, reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import UserRegistrationForm
from django.http import HttpResponseForbidden
from django.forms import modelformset_factory, inlineformset_factory
from django.views import View


# Create your views here.
###################################################################################
# ここから顧客用
###################################################################################
class LoginView(LoginView):
    form_class = AuthenticationForm
    template_name = 'reservations/login.html'


class LogoutView(LogoutView):
    template_name = 'reservations/logout.html'


class MenuUserView(LoginRequiredMixin, TemplateView):
    template_name = 'reservations/menu_user.html'


class ReservationListView(LoginRequiredMixin, ListView):
    model = Reservation
    template_name = 'reservations/reservation_list.html'  # 使用するテンプレート名
    context_object_name = 'reservations'  # テンプレートで使用するオブジェクト名

    def get_queryset(self):
        phone_number = self.request.GET.get('phone_number', '')  # URLクエリパラメータから電話番号を取得
        if phone_number:
            today = now().date()  # 現在の日付を取得
            return Reservation.objects.filter(
                phone_number=phone_number,
                start__date__gte=today  # 今日以降の予約を取得
            ).order_by('start')  # 予約日が近い順に並べる
        return Reservation.objects.none()  # 電話番号が渡されていない場合は空のクエリセットを返す

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['phone_number'] = self.request.GET.get('phone_number', '')  # テンプレートに電話番号を渡す
        return context

class ReservationDetailView(LoginRequiredMixin, TemplateView):
    template_name = "reservations/reservation_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reservation_id = kwargs.get("pk")
        reservation = get_object_or_404(Reservation, id=reservation_id)
        reservation_items = ReservationItem.objects.filter(reservation=reservation)

        # 注文メニューの詳細を計算
        reservation_details = []
        total_excl_tax = 0

        for item in reservation_items:
            item_total = item.item.price * item.quantity  # 小計
            total_excl_tax += item_total
            reservation_details.append({
                "name": item.item.name,
                "quantity": item.quantity,
                "price": item.item.price,
                "total": item_total,
            })

        tax_amount = total_excl_tax * 0.1  # 消費税額
        discount_amount = int((total_excl_tax + tax_amount) * 0.1)  # 割引額（切り捨て）
        total_incl_tax = total_excl_tax + tax_amount - discount_amount

        # コンテキストに追加
        context.update({
            "reservation": reservation,
            "reservation_details": reservation_details,
            "total_excl_tax": total_excl_tax,
            "tax_amount": tax_amount,
            "discount_amount": discount_amount,
            "total_incl_tax": total_incl_tax,
        })

        return context

class ReservationEditView(LoginRequiredMixin, UpdateView):
    model = Reservation
    form_class = ReservationForm
    template_name = 'reservations/reservation_edit.html'

    def get_object(self):
        reservation_id = self.kwargs.get('pk')
        return get_object_or_404(Reservation, id=reservation_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reservation = self.get_object()
        reservation_items = reservation.items.all()
        context['reservation_items'] = reservation_items
        return context

    def form_valid(self, form):
        reservation = form.save(commit=False)

        # 予約内容を保存
        reservation.save()

        # 既存の注文を削除（重複しないように）
        reservation.items.all().delete()

        # 注文メニューを保存（フォームから入力された数量を使って）
        form.save_menus(reservation)

        # 予約詳細ページへリダイレクト
        return redirect('reservation_detail', pk=reservation.id)

class ReservationDeleteView(LoginRequiredMixin, DeleteView):
    model = Reservation
    success_url = reverse_lazy('reservation_list')

class CalendarView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'reservations/calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = datetime.now().date()  # 今日の日付を取得
        max_seats = 8  # 1時間あたりの最大席数

        # 祝日を settings.py から取得
        public_holidays = settings.PUBLIC_HOLIDAYS

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
        for hour in range(9, 17):  # 営業時間
            row = {}
            for day in days:
                start_time = make_aware(datetime.combine(day, datetime.min.time().replace(hour=hour)))
                end_time = start_time + timedelta(hours=1)

                # 予約済み席数を計算
                reserved_seats = Reservation.objects.filter(
                    start__lt=end_time,
                    end__gt=start_time
                ).aggregate(total=Sum('seat_count'))['total'] or 0

                # 残り席数を計算
                remaining_seats = max_seats - reserved_seats
                row[day] = remaining_seats

            calendar[hour] = row

        context['public_holidays'] = public_holidays
        context['calendar'] = calendar
        context['days'] = days
        context['start_day'] = start_day
        context['end_day'] = end_day
        context['before'] = days[0] - timedelta(days=7)
        context['next'] = days[-1] + timedelta(days=1)
        context['today'] = today

        return context


class ReservationView(LoginRequiredMixin, CreateView):
    template_name = 'reservations/reservation_form.html'
    form_class = ReservationForm  # 顧客用フォームを指定
    model = Reservation

    def get_initial(self):
        initial = super().get_initial()

        year = self.kwargs.get('year')
        month = self.kwargs.get('month')
        day = self.kwargs.get('day')
        hour = self.kwargs.get('hour')

        if year and month and day and hour:
            start_time = datetime(year=int(year), month=int(month), day=int(day), hour=int(hour))
            initial['start'] = make_aware(start_time)

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.get_form()

        items_fields = [field for field in form if field.name.startswith('item_')]
        other_fields = [field for field in form if not field.name.startswith('item_')]

        context['form'] = form
        context['items_fields'] = items_fields
        context['other_fields'] = other_fields

        return context

    def form_valid(self, form):
        reservation = form.save(commit=False)
        reservation.end = reservation.start + timedelta(hours=reservation.hour)

        # 同時間帯の予約済み座席数を計算
        total_reserved_seats = Reservation.objects.filter(
            start__lt=reservation.end,
            end__gt=reservation.start
        ).aggregate(Sum('seat_count'))['seat_count__sum'] or 0

        if total_reserved_seats + reservation.seat_count > 8:
            form.add_error(None, "この時間帯の席数が不足しています。")
            print("フォームにエラーがあります(form_valid内)", form.errors)  # デバッグ用
            return self.form_invalid(form)

        reservation.save()
        form.save_menus(reservation)

        return redirect(reverse('complete') + f'?reservation_id={reservation.id}')


def form_invalid(self, form):
    print("フォームにエラーがあります(form_invalid)", form.errors)  # デバッグ用
    return self.render_to_response(self.get_context_data(form=form))


class ReservationCompleteView(LoginRequiredMixin, TemplateView):
    template_name = 'reservations/reservation_complete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reservation_id = self.request.GET.get("reservation_id")
        reservation = get_object_or_404(Reservation, id=reservation_id)
        reservation_items = ReservationItem.objects.filter(reservation=reservation)

        reservation_details = []
        total_excl_tax = 0

        for item in reservation_items:
            item_total = item.item.price * item.quantity
            total_excl_tax += item_total
            reservation_details.append({
                "name": item.item.name,
                "quantity": item.quantity,
                "price": item.item.price,
                "total": item_total,
            })

        tax_amount = total_excl_tax * 0.1
        discount_amount = math.floor((total_excl_tax + tax_amount) * 0.1)
        total_incl_tax = total_excl_tax + tax_amount - discount_amount

        context.update({
            "reservation": reservation,
            "reservation_details": reservation_details,
            "total_excl_tax": total_excl_tax,
            "tax_amount": tax_amount,
            "discount_amount": discount_amount,
            "total_incl_tax": total_incl_tax,
        })

        return context

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # 新規ユーザーを作成
            user = User.objects.create_user(username=username, password=password)

            # ユーザーが作成されたことを通知
            messages.success(request, f'{username} さん、アカウントが作成されました！')

            return redirect('login')  # ログインページにリダイレクト

    else:
        form = UserRegistrationForm()

    return render(request, 'reservations/register.html', {'form': form})


###################################################################################
# ここから店舗用
###################################################################################
class StaffLoginView(LoginView):
    template_name = 'reservations/staff_login.html'  # スタッフ用ログインページ
    form_class = AuthenticationForm

    def form_valid(self, form):
        user = form.get_user()
        if not user.is_staff:  # スタッフ権限を確認
            return HttpResponseForbidden("スタッフ専用ページです。ログインできません。")
        return super().form_valid(form)

    def get_success_url(self):
        return '/menu_shop/'  # スタッフログイン後のリダイレクト先

class MenuShopView(LoginRequiredMixin, TemplateView):
    template_name = 'reservations/menu_shop.html'

class AllReservationsListView(LoginRequiredMixin, ListView):
    model = Reservation
    template_name = 'reservations/all_reservations_list.html'  # 使用するテンプレート
    context_object_name = 'reservations'  # テンプレートで使用するオブジェクト名

    def get_queryset(self):
        # 現在の日時から2時間前までの予約を含む
        one_hour_ago = now() - timedelta(hours=2)  # 現在時刻から2時間前
        return Reservation.objects.filter(start__gte=one_hour_ago).order_by('start')

class ShopCalendarView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'reservations/shop_calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = datetime.now().date()  # 今日の日付を取得
        max_seats = 8  # 1時間あたりの最大席数

        # 祝日を settings.py から取得
        public_holidays = settings.PUBLIC_HOLIDAYS

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
        for hour in range(9, 17):  # 営業時間
            row = {}
            for day in days:
                start_time = make_aware(datetime.combine(day, datetime.min.time().replace(hour=hour)))
                end_time = start_time + timedelta(hours=1)

                # 予約済み席数を計算
                reserved_seats = Reservation.objects.filter(
                    start__lt=end_time,
                    end__gt=start_time
                ).aggregate(total=Sum('seat_count'))['total'] or 0

                # 残り席数を計算
                remaining_seats = max_seats - reserved_seats
                row[day] = remaining_seats

            calendar[hour] = row

        context['public_holidays'] = public_holidays
        context['calendar'] = calendar
        context['days'] = days
        context['start_day'] = start_day
        context['end_day'] = end_day
        context['before'] = days[0] - timedelta(days=7)
        context['next'] = days[-1] + timedelta(days=1)
        context['today'] = today

        return context

class ShopReservationView(LoginRequiredMixin, CreateView):
    template_name = 'reservations/shop_reservation_form.html'
    form_class = ShopReservationForm
    model = Reservation

    def get_initial(self):
        initial = super().get_initial()

        year = self.kwargs.get('year')
        month = self.kwargs.get('month')
        day = self.kwargs.get('day')
        hour = self.kwargs.get('hour')

        if year and month and day and hour:
            start_time = datetime(year=int(year), month=int(month), day=int(day), hour=int(hour))
            initial['start'] = make_aware(start_time)

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.get_form()

        items_fields = [field for field in form if field.name.startswith('item_')]
        other_fields = [field for field in form if not field.name.startswith('item_')]

        context['form'] = form
        context['items_fields'] = items_fields
        context['other_fields'] = other_fields

        return context

    def form_valid(self, form):
        reservation = form.save(commit=False)
        reservation.end = reservation.start + timedelta(hours=reservation.hour)

        # 同時間帯の予約済み座席数を計算
        total_reserved_seats = Reservation.objects.filter(
            start__lt=reservation.end,
            end__gt=reservation.start
        ).aggregate(Sum('seat_count'))['seat_count__sum'] or 0

        if total_reserved_seats + reservation.seat_count > 8:
            form.add_error(None, "この時間帯の席数が不足しています。")
            return self.form_invalid(form)

        reservation.save()
        form.save_menus(reservation)

        return redirect(reverse('menu_shop_complete') + f'?reservation_id={reservation.id}')

class ShopReservationCompleteView(LoginRequiredMixin, TemplateView):
    template_name = 'reservations/shop_reservation_complete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reservation_id = self.request.GET.get("reservation_id")
        reservation = get_object_or_404(Reservation, id=reservation_id)
        reservation_items = ReservationItem.objects.filter(reservation=reservation)

        reservation_details = []
        total_excl_tax = 0

        for item in reservation_items:
            item_total = item.item.price * item.quantity
            total_excl_tax += item_total
            reservation_details.append({
                "name": item.item.name,
                "quantity": item.quantity,
                "price": item.item.price,
                "total": item_total,
            })

        tax_amount = total_excl_tax * 0.1
        discount_amount = math.floor((total_excl_tax + tax_amount) * 0.1)
        total_incl_tax = total_excl_tax + tax_amount - discount_amount

        context.update({
            "reservation": reservation,
            "reservation_details": reservation_details,
            "total_excl_tax": total_excl_tax,
            "tax_amount": tax_amount,
            "discount_amount": discount_amount,
            "total_incl_tax": total_incl_tax,
        })

        return context