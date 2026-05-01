from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tickets.models import Ticket, Status, Priority
from departments.models import Department, Category
from identity.models import User, Role

# Export fonksiyonları mevcut views.py'den kullanılır (dosya döndürdükleri için)
from .views import export_csv, export_excel, export_pdf


# Raporlama dashboard'u — tüm istatistikleri JSON olarak döndürür
class ReportDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = {}
        user = request.user

        dept_qs = Department.objects.all()
        cat_qs = Category.objects.all()
        user_qs = User.objects.filter(role__in=[Role.AGENT, Role.MANAGER])
        ticket_qs = Ticket.objects.all()

        if user.role == Role.MANAGER:
            dept_qs = dept_qs.filter(id=user.department_id)
            cat_qs = cat_qs.filter(department=user.department)
            user_qs = user_qs.filter(department=user.department)
            ticket_qs = ticket_qs.filter(department=user.department)

        # Departman Performans Raporları
        departments = dept_qs.annotate(
            total_tickets=Count('tickets'),
            open_tickets=Count('tickets', filter=Q(tickets__status=Status.OPEN)),
            in_progress_tickets=Count('tickets', filter=Q(tickets__status=Status.IN_PROGRESS)),
            closed_tickets=Count('tickets', filter=Q(tickets__status=Status.CLOSED)),
        ).order_by('-total_tickets')

        data['departments'] = [
            {
                'id': d.id,
                'name': d.name,
                'total_tickets': d.total_tickets,
                'open_tickets': d.open_tickets,
                'in_progress_tickets': d.in_progress_tickets,
                'closed_tickets': d.closed_tickets,
            }
            for d in departments
        ]

        # Departman bazlı ortalama çözüm süresi (saat cinsinden)
        dept_avg_resolution = []
        for dept in departments:
            closed = Ticket.objects.filter(
                department=dept,
                status=Status.CLOSED,
                closed_at__isnull=False,
            )
            if closed.exists():
                durations = [
                    (t.closed_at - t.created_at).total_seconds() / 3600
                    for t in closed
                ]
                avg_hours = round(sum(durations) / len(durations), 1)
            else:
                avg_hours = None

            dept_avg_resolution.append({
                'name': dept.name,
                'avg_hours': avg_hours,
                'closed_count': closed.count(),
            })

        data['dept_avg_resolution'] = dept_avg_resolution

        # En çok talep alan kategoriler (ilk 10)
        top_categories = cat_qs.annotate(
            ticket_count=Count('tickets'),
        ).filter(ticket_count__gt=0).order_by('-ticket_count')[:10]

        data['top_categories'] = [
            {'id': c.id, 'name': c.name, 'department': c.department.name, 'ticket_count': c.ticket_count}
            for c in top_categories.select_related('department')
        ]

        # Personel İş Yükü Raporları
        personnel = user_qs.annotate(
            active_tickets=Count(
                'assigned_tickets',
                filter=Q(assigned_tickets__status=Status.IN_PROGRESS),
            ),
            total_closed=Count(
                'assigned_tickets',
                filter=Q(assigned_tickets__status=Status.CLOSED),
            ),
        ).order_by('-active_tickets')

        data['personnel'] = [
            {
                'id': p.id,
                'username': p.username,
                'full_name': p.get_full_name() or p.username,
                'active_tickets': p.active_tickets,
                'total_closed': p.total_closed,
            }
            for p in personnel
        ]

        # En çok bilet üstlenen personel (ilk 10)
        top_personnel = user_qs.annotate(
            total_assigned=Count('assigned_tickets'),
        ).filter(total_assigned__gt=0).order_by('-total_assigned')[:10]

        data['top_personnel'] = [
            {'id': p.id, 'full_name': p.get_full_name() or p.username, 'total_assigned': p.total_assigned}
            for p in top_personnel
        ]

        # Personel bazlı ortalama çözüm süresi
        personnel_avg = []
        for p in top_personnel:
            closed = Ticket.objects.filter(
                assigned_to=p,
                status=Status.CLOSED,
                closed_at__isnull=False,
            )
            if closed.exists():
                durations = [
                    (t.closed_at - t.created_at).total_seconds() / 3600
                    for t in closed
                ]
                avg_hours = round(sum(durations) / len(durations), 1)
            else:
                avg_hours = None

            personnel_avg.append({
                'name': p.get_full_name() or p.username,
                'avg_hours': avg_hours,
            })

        data['personnel_avg'] = personnel_avg

        # Genel İstatistikler
        data['total_tickets'] = ticket_qs.count()
        data['open_count'] = ticket_qs.filter(status=Status.OPEN).count()
        data['in_progress_count'] = ticket_qs.filter(status=Status.IN_PROGRESS).count()
        data['closed_count'] = ticket_qs.filter(status=Status.CLOSED).count()

        # Aylık bilet trend verisi (son 6 ay)
        today = timezone.now()
        monthly_data = []
        for i in range(5, -1, -1):
            month_start = (today - timedelta(days=i * 30)).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0,
            )
            if i > 0:
                month_end = (today - timedelta(days=(i - 1) * 30)).replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0,
                )
            else:
                month_end = today

            count = ticket_qs.filter(
                created_at__gte=month_start,
                created_at__lt=month_end,
            ).count()

            monthly_data.append({
                'label': month_start.strftime('%b %Y'),
                'count': count,
            })

        data['monthly_trend'] = monthly_data

        # Departman karşılaştırma (çubuk grafik verisi)
        data['dept_comparison'] = [
            {
                'name': d.name,
                'open': d.open_tickets,
                'in_progress': d.in_progress_tickets,
                'closed': d.closed_tickets,
            }
            for d in departments
        ]

        return Response(data)
