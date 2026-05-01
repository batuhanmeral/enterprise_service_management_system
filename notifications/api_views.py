from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer, NotificationDetailSerializer


# Bildirim listeleme — sadece giriş yapan kullanıcının bildirimleri
class NotificationListAPIView(ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user,
        ).select_related('ticket')

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Okunmamış bildirim sayısını ekle
        response.data['unread_count'] = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()
        return response


# Bildirim detay — otomatik okundu işaretleme
class NotificationDetailAPIView(RetrieveAPIView):
    serializer_class = NotificationDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user,
        ).select_related('ticket')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Bildirimi görüntüleyince otomatik okundu işaretle
        instance.mark_as_read()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


# Tek bildirimi okundu olarak işaretle
class NotificationMarkReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk)
        except Notification.DoesNotExist:
            return Response(
                {'detail': 'Bildirim bulunamadı.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if notification.recipient != request.user:
            return Response(
                {'detail': 'Bu bildirime erişim yetkiniz yok.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        notification.mark_as_read()
        return Response({'detail': 'Bildirim okundu olarak işaretlendi.'})


# Tüm bildirimleri toplu okundu olarak işaretle
class NotificationMarkAllReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(is_read=True)

        return Response({'detail': f'{count} bildirim okundu olarak işaretlendi.', 'count': count})


# Bildirim silme
class NotificationDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk)
        except Notification.DoesNotExist:
            return Response(
                {'detail': 'Bildirim bulunamadı.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if notification.recipient != request.user:
            return Response(
                {'detail': 'Bu bildirime erişim yetkiniz yok.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Okunmamış bildirim sayısı — navbar badge için
class NotificationUnreadCountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()
        return Response({'unread_count': count})
