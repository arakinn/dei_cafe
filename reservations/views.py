import datetime
import math
from django.db.models import Sum
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from typing import Any
from django.shortcuts import render
from django.core.paginator import Paginator
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from django.utils.timezone import now
from .models import Reservation, ReservationItem, Items, Comment
from django.views import generic
from django.conf import settings
from .forms import ReservationForm, ItemForm, ShopReservationForm, CommentForm
from django.core.exceptions import ValidationError
from django.urls import reverse, reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import UserRegistrationForm
from django.http import HttpResponseForbidden
from django.views import View
from django.db import models
from django.contrib.messages.views import SuccessMessageMixin

# Create your views here.
###################################################################################
# ここから顧客用
###################################################################################
class LoginView(LoginView):
    form_class = AuthenticationForm
    template_name = 'reservations/login.html'

    # 店舗からのお知らせ表示
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comments'] = Comment.objects.all().order_by('-created_at')[:3]  # 最新3件を表示
        return context


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

        tax_amount = math.floor(total_excl_tax * 0.1)  # 消費税額（切り捨て）
        discount_amount = math.floor((total_excl_tax + tax_amount) * 0.1)  # 割引額（切り捨て）
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
    success_url = reverse_lazy('menu_user')


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

        form = context.get('form') 
        return context

    def form_valid(self, form):
        reservation = form.save(commit=False)
        reservation.end = reservation.start + timedelta(hours=reservation.hour)
        
        reservation.save()
        form.save_menus(reservation)

        return redirect(reverse('complete') + f'?reservation_id={reservation.id}')
    
    def form_invalid(self, form):
        # フォームエラーをコンテキストに渡す
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

        tax_amount = math.floor(total_excl_tax * 0.1)
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

###################################################################################
# 新規ユーザー登録
###################################################################################
def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # 新規ユーザーを作成
            user = User.objects.create_user(username=username, password=password)

            return redirect('login')  # ログインページにリダイレクト

    else:
        form = UserRegistrationForm()

    return render(request, 'reservations/register.html', {'form': form})


###################################################################################
# ここから店舗用
###################################################################################
class StaffLoginView(LoginView):
    template_name = 'reservations/staff_login.html'
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
    paginate_by = 10

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
    form_class = ShopReservationForm #店舗用フォームを指定
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

        tax_amount = math.floor(total_excl_tax * 0.1) #消費税小数点以下切り捨て
        discount_amount = math.floor((total_excl_tax + tax_amount) * 0.1) #割引額小数点以下切り捨て
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


class ShopReservationDetailView(LoginRequiredMixin, TemplateView):
    template_name = "reservations/shop_reservation_detail.html"

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

        tax_amount = math.floor(total_excl_tax * 0.1)  # 消費税額（切り捨て）
        discount_amount = math.floor((total_excl_tax + tax_amount) * 0.1)  # 割引額（切り捨て）
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


class ShopReservationEditView(LoginRequiredMixin, UpdateView):
    model = Reservation
    form_class = ShopReservationForm
    template_name = 'reservations/shop_reservation_edit.html'

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
        return redirect('menu_shop_detail', pk=reservation.id)


class ShopReservationDeleteView(LoginRequiredMixin, DeleteView):
    template_name = 'reservations/shop_reservation_confirm_delete.html'
    model = Reservation
    success_url = reverse_lazy('menu_shop_list')


class ItemListView(LoginRequiredMixin, ListView):
    model = Items
    template_name = 'reservations/item_list.html'
    context_object_name = 'items'  # テンプレート内で使う変数名

    def get_queryset(self):
        # sort フィールドの昇順で並び替え
        return Items.objects.all().order_by('sort')

class ItemCreateView(LoginRequiredMixin, CreateView):
    model = Items
    form_class = ItemForm  # 使用するフォーム
    template_name = 'reservations/item_form.html'
    success_url = '/menu/'  # 作成後のリダイレクト先

    def get_initial(self):
        initial = super().get_initial()
        initial['order_deadline'] = timezone.now().date()
        return initial


class ItemUpdateView(LoginRequiredMixin, UpdateView):
    model = Items
    form_class = ItemForm
    template_name = 'reservations/item_edit.html'
    success_url = '/menu/'  # 編集後のリダイレクト先


class ItemDeleteView(DeleteView):
    model = Items
    template_name = 'reservations/item_confirm_delete.html'  # 確認画面のテンプレート
    success_url = reverse_lazy('menu')  # 削除後のリダイレクト先


class CommentManageView(LoginRequiredMixin, ListView):
    model = Comment
    template_name = 'reservations/comment_manage.html'
    paginate_by = 5  # 1ページあたり5件表示
    context_object_name = 'comments'
    ordering = ['-created_at']  # 最新順に表示

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        return context

    def post(self, request, *args, **kwargs):
        form = CommentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('comment_manage')  # 自分自身のページへリダイレクト
        return self.get(request)


class CommentDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Comment
    template_name = 'reservations/comment_confirm_delete.html'
    success_url = reverse_lazy('comment_manage')  # 削除後にリダイレクト

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.object  # コメントデータをテンプレートに渡す
        return context