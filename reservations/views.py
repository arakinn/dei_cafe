import datetime
import math
from django.db.models import Sum
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
    template_name = 'reservations/logout.html'


class MenuUserView(TemplateView):
    template_name = 'reservations/menu_user.html'


class ReservationListView(TemplateView):
    template_name = 'reservations/reservation_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        phone_number = self.request.GET.get('phone_number', '123456789')
        context['phone_number'] = phone_number
        return context


class CalendarView(generic.TemplateView):
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



class ReservationView(CreateView):
    template_name = 'reservations/reservation_form.html'
    form_class = ReservationForm
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

        return redirect(reverse('complete') + f'?reservation_id={reservation.id}')


class ReservationCompleteView(TemplateView):
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
