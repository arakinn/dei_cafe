"""
URL configuration for dei_cafe project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from reservations import views
from django.contrib.auth.views import LoginView, LogoutView
from reservations.views import LoginView, ReservationView, ReservationCompleteView, ReservationDetailView, ReservationDeleteView, AllReservationsListView, ShopReservationView, ShopReservationCompleteView, ItemListView, ItemCreateView, ItemUpdateView, ItemDeleteView, ShopReservationEditView, ShopReservationDeleteView, CommentManageView

urlpatterns = [
    #ここから顧客用
    path('admin/', admin.site.urls),
    path('', views.LoginView.as_view(), name="login"),
    path('logout/', views.LogoutView.as_view(), name="logout"),
    path('menu_user/', views.MenuUserView.as_view(), name="menu_user"),
    path('reserve/list/', views.ReservationListView.as_view(), name="reservation_list"),
    path('reserve/detail/<int:pk>/', ReservationDetailView.as_view(), name="reservation_detail"),
    path('reserve/edit/<int:pk>/', views.ReservationEditView.as_view(), name="reservation_edit"),
    path('reserve/delete/<int:pk>/', views.ReservationDeleteView.as_view(), name="reservation_delete"),
    path('calendar/', views.CalendarView.as_view(), name="calendar"),
    path('calendar/<int:year>/<int:month>/<int:day>/', views.CalendarView.as_view(), name="calendar"),
    path('reserve/<int:year>/<int:month>/<int:day>/<int:hour>/', views.ReservationView.as_view(), name="reserve"),
    path('complete/', views.ReservationCompleteView.as_view(), name="complete"),
    path('register/', views.register, name="register"),
    #ここから店舗用
    path('staff_login/', views.StaffLoginView.as_view(), name="staff_login"),
    path('menu_shop/', views.MenuShopView.as_view(), name="menu_shop"),
    path('menu_shop/list/', views.AllReservationsListView.as_view(), name="menu_shop_list"),
    path('menu_shop/detail/<int:pk>/', views.ShopReservationDetailView.as_view(), name="menu_shop_detail"),
    path('menu_shop/edit/<int:pk>/', views.ShopReservationEditView.as_view(), name="menu_shop_edit"),
    path('menu_shop/delete/<int:pk>/', views.ShopReservationDeleteView.as_view(), name="menu_shop_delete"),
    path('menu_shop/calendar/', views.ShopCalendarView.as_view(), name="menu_shop_calendar"),
    path('menu_shop/calendar/<int:year>/<int:month>/<int:day>/', views.ShopCalendarView.as_view(), name="menu_shop_calendar"),
    path('menu_shop/reserve/<int:year>/<int:month>/<int:day>/<int:hour>/',ShopReservationView.as_view(),name="menu_shop_reserve"),
    path('menu_shop/complete/', views.ShopReservationCompleteView.as_view(), name="menu_shop_complete"),
    path('menu/', views.ItemListView.as_view(), name='menu'),
    path('menu/create/', views.ItemCreateView.as_view(), name='menu_create'),
    path('menu/<int:pk>/edit/', views.ItemUpdateView.as_view(), name='menu_edit'),
    path('menu/<int:pk>/delete/', views.ItemDeleteView.as_view(), name='menu_delete'),
    path('menu_shop/comments/', views.CommentManageView.as_view(), name='comment_manage'),
    path('menu_shop/comment/delete/<int:pk>/', views.CommentDeleteView.as_view(), name='comment_delete'),
]
