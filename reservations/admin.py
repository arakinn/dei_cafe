from django.contrib import admin
from .models import Reservation, Items, ReservationItem, Comment

# ReservationItem をインライン表示する設定
class ReservationItemInline(admin.TabularInline):
    model = ReservationItem
    extra = 1  # デフォルトで表示する空の行の数

class ReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'start')
    search_fields = ('phone_number',)
    inlines = [ReservationItemInline]  # ReservationItem をインライン表示

class ItemsAdmin(admin.ModelAdmin):
    list_display = ('sort', 'category', 'name', 'price')

class ReservationItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'reservation', 'item', 'quantity')

class CommentAdmin(admin.ModelAdmin):
    list_display = ('content', 'created_at')

# モデルを管理サイトに登録
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(Items, ItemsAdmin)
admin.site.register(ReservationItem, ReservationItemAdmin)
admin.site.register(Comment, CommentAdmin)