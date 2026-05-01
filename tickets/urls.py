from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    # Bilet listeleme (rol bazlı filtrelemeli)
    path('', views.TicketListView.as_view(), name='ticket_list'),

    # Yeni bilet oluşturma
    path('create/', views.TicketCreateView.as_view(), name='ticket_create'),

    # Bilet detayı
    path('<int:pk>/', views.TicketDetailView.as_view(), name='ticket_detail'),

    # Bilet güncelleme
    path('<int:pk>/update/', views.TicketUpdateView.as_view(), name='ticket_update'),

    # Bilet silme
    path('<int:pk>/delete/', views.ticket_delete_view, name='ticket_delete'),

    # Bilet üstlenme (İşlemde)
    path('<int:pk>/take/', views.ticket_take_view, name='ticket_take'),

    # Bilet kapatma
    path('<int:pk>/close/', views.ticket_close_view, name='ticket_close'),

    # Bilet transfer
    path('<int:pk>/transfer/', views.ticket_transfer_view, name='ticket_transfer'),

    # Bilet yorum ekleme
    path('<int:pk>/comment/', views.ticket_add_comment_view, name='ticket_add_comment'),

    # Bilet yeniden açma (CLOSED -> OPEN)
    path('<int:pk>/reopen/', views.ticket_reopen_view, name='ticket_reopen'),
]
