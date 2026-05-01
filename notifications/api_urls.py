from django.urls import path

from . import api_views

urlpatterns = [
    # Bildirim listeleme
    path('', api_views.NotificationListAPIView.as_view(), name='api_notification_list'),
    # Tüm bildirimleri okundu işaretle
    path('mark-all-read/', api_views.NotificationMarkAllReadAPIView.as_view(), name='api_notification_mark_all_read'),
    # Okunmamış bildirim sayısı
    path('unread-count/', api_views.NotificationUnreadCountAPIView.as_view(), name='api_notification_unread_count'),
    # Bildirim detay
    path('<int:pk>/', api_views.NotificationDetailAPIView.as_view(), name='api_notification_detail'),
    # Tek bildirimi okundu işaretle
    path('<int:pk>/read/', api_views.NotificationMarkReadAPIView.as_view(), name='api_notification_mark_read'),
    # Bildirim silme
    path('<int:pk>/delete/', api_views.NotificationDeleteAPIView.as_view(), name='api_notification_delete'),
]
