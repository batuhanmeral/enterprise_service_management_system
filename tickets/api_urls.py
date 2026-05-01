from django.urls import path

from . import api_views

urlpatterns = [
    # Bilet listeleme ve oluşturma
    path('', api_views.TicketListCreateAPIView.as_view(), name='api_ticket_list'),
    # Bilet detay, güncelleme ve silme
    path('<int:pk>/', api_views.TicketDetailAPIView.as_view(), name='api_ticket_detail'),
    # Bilet üstlenme (OPEN → IN_PROGRESS)
    path('<int:pk>/take/', api_views.TicketTakeAPIView.as_view(), name='api_ticket_take'),
    # Bilet kapatma (IN_PROGRESS → CLOSED)
    path('<int:pk>/close/', api_views.TicketCloseAPIView.as_view(), name='api_ticket_close'),
    # Bilet transfer (departmanlar arası)
    path('<int:pk>/transfer/', api_views.TicketTransferAPIView.as_view(), name='api_ticket_transfer'),
]
