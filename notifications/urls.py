from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Bildirim listeleme
    path('', views.NotificationListView.as_view(), name='notification_list'),

    # Bildirim detay
    path('<int:pk>/', views.NotificationDetailView.as_view(), name='notification_detail'),

    # Tek bildirimi okundu olarak işaretle
    path('<int:pk>/read/', views.notification_mark_read_view, name='notification_mark_read'),

    # Bildirim silme
    path('<int:pk>/delete/', views.notification_delete_view, name='notification_delete'),

    # Tüm bildirimleri okundu olarak işaretle
    path('mark-all-read/', views.notification_mark_all_read_view, name='notification_mark_all_read'),
]
