import django_filters

from .models import Ticket, Status, Priority


# Bilet listesi için kapsamlı filtre seti
# Kullanım: ?status=OPEN&priority=HIGH&department=2&created_at__gte=2026-01-01
class TicketFilter(django_filters.FilterSet):
    # Tek değerli alanlar
    status = django_filters.ChoiceFilter(choices=Status.choices)
    priority = django_filters.ChoiceFilter(choices=Priority.choices)

    # Tarih aralığı filtreleri
    created_at = django_filters.DateFromToRangeFilter()
    closed_at = django_filters.DateFromToRangeFilter()

    # Konu içinde arama (?subject=fatura)
    subject = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Ticket
        fields = {
            'department': ['exact'],
            'category': ['exact'],
            'sender': ['exact'],
            'assigned_to': ['exact', 'isnull'],
        }
