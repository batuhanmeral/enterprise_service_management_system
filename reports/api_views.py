import calendar

from django.db.models import Avg, Count, ExpressionWrapper, F, Q, DurationField
from django.utils import timezone

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from config.permissions import IsManagerOrAdmin

from tickets.models import Ticket, Status
from departments.models import Department, Category
from identity.models import User, Role

from .views import export_csv, export_excel, export_pdf, _get_monthly_trend


# Raporlama dashboard'u — tüm istatistikleri JSON olarak döndürür
@extend_schema(tags=['reports'], responses={200: OpenApiResponse(description='Tüm istatistik JSON verisi')})
class ReportDashboardAPIView(APIView):
    # Raporlar gizli kurumsal istatistik içerir; sadece MANAGER ve ADMIN erişir.
    permission_classes = [IsManagerOrAdmin]

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

        # Departman bazlı ortalama çözüm süresi — ticket_qs scope'una uyar
        dept_resolution_qs = (
            ticket_qs
            .filter(status=Status.CLOSED, closed_at__isnull=False)
            .values('department_id')
            .annotate(
                avg_duration=Avg(
                    ExpressionWrapper(F('closed_at') - F('created_at'), output_field=DurationField())
                ),
                closed_count=Count('id'),
            )
        )
        dept_resolution_map = {r['department_id']: r for r in dept_resolution_qs}

        dept_avg_resolution = []
        for dept in departments:
            res = dept_resolution_map.get(dept.pk)
            if res and res['avg_duration']:
                avg_hours = round(res['avg_duration'].total_seconds() / 3600, 1)
                closed_count = res['closed_count']
            else:
                avg_hours = None
                closed_count = 0
            dept_avg_resolution.append({
                'name': dept.name,
                'avg_hours': avg_hours,
                'closed_count': closed_count,
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

        # Personel bazlı ortalama çözüm süresi — ticket_qs scope'una uyar
        personnel_resolution_qs = (
            ticket_qs
            .filter(status=Status.CLOSED, closed_at__isnull=False, assigned_to__isnull=False)
            .values('assigned_to_id')
            .annotate(
                avg_duration=Avg(
                    ExpressionWrapper(F('closed_at') - F('created_at'), output_field=DurationField())
                ),
            )
        )
        personnel_resolution_map = {r['assigned_to_id']: r for r in personnel_resolution_qs}

        personnel_avg = []
        for p in top_personnel:
            res = personnel_resolution_map.get(p.pk)
            if res and res['avg_duration']:
                avg_hours = round(res['avg_duration'].total_seconds() / 3600, 1)
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

        # Aylık bilet trend verisi (son 6 ay) — takvim tabanlı doğru ay hesabı
        labels, counts = _get_monthly_trend(ticket_qs)
        data['monthly_trend'] = [
            {'label': label, 'count': count}
            for label, count in zip(labels, counts)
        ]

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
