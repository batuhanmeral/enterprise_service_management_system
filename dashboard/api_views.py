from django.db.models import Count, Q

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tickets.models import Ticket, Status
from notifications.models import Notification
from identity.models import Role
from identity.serializers import UserShortSerializer
from tickets.serializers import TicketListSerializer
from notifications.serializers import NotificationSerializer


# Rol bazlı ana sayfa dashboard'u — JSON
@extend_schema(tags=['dashboard'], responses={200: OpenApiResponse(description='Rol bazlı dashboard verisi')})
class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {'role': user.role}

        # Çalışan (EMPLOYEE): Kendi biletleri
        if user.role == Role.EMPLOYEE:
            my_tickets = Ticket.objects.filter(sender=user)
            data['my_open'] = my_tickets.filter(status=Status.OPEN).count()
            data['my_in_progress'] = my_tickets.filter(status=Status.IN_PROGRESS).count()
            data['my_closed'] = my_tickets.filter(status=Status.CLOSED).count()
            data['recent_tickets'] = TicketListSerializer(
                my_tickets.select_related('department', 'sender', 'assigned_to', 'category')[:5],
                many=True,
            ).data

        # Personel (AGENT): Departman bilet havuzu
        elif user.role == Role.AGENT:
            dept_tickets = Ticket.objects.filter(department=user.department)
            data['dept_open'] = dept_tickets.filter(status=Status.OPEN).count()
            data['dept_in_progress'] = dept_tickets.filter(status=Status.IN_PROGRESS).count()
            data['my_assigned'] = TicketListSerializer(
                Ticket.objects.filter(
                    assigned_to=user, status=Status.IN_PROGRESS,
                ).select_related('sender', 'department', 'assigned_to', 'category')[:5],
                many=True,
            ).data
            data['waiting_tickets'] = TicketListSerializer(
                dept_tickets.filter(status=Status.OPEN).select_related('sender', 'department', 'assigned_to', 'category')[:5],
                many=True,
            ).data

        # Yönetici (MANAGER): Departman istatistikleri
        elif user.role == Role.MANAGER:
            dept_tickets = Ticket.objects.filter(department=user.department)
            data['dept_total'] = dept_tickets.count()
            data['dept_open'] = dept_tickets.filter(status=Status.OPEN).count()
            data['dept_in_progress'] = dept_tickets.filter(status=Status.IN_PROGRESS).count()
            data['dept_closed'] = dept_tickets.filter(status=Status.CLOSED).count()

            # Personel iş yükü
            from identity.models import User
            personnel_qs = User.objects.filter(
                department=user.department,
                role__in=[Role.AGENT, Role.MANAGER],
            ).annotate(
                active=Count('assigned_tickets', filter=Q(assigned_tickets__status=Status.IN_PROGRESS)),
            ).order_by('-active')[:10]

            data['personnel_load'] = [
                {
                    'id': p.id,
                    'username': p.username,
                    'full_name': p.get_full_name() or p.username,
                    'active': p.active,
                }
                for p in personnel_qs
            ]

            data['recent_tickets'] = TicketListSerializer(
                dept_tickets.select_related('sender', 'assigned_to', 'department', 'category')[:5],
                many=True,
            ).data

        # Admin: Sistem geneli
        elif user.role == Role.ADMIN:
            data['total_tickets'] = Ticket.objects.count()
            data['total_open'] = Ticket.objects.filter(status=Status.OPEN).count()
            data['total_in_progress'] = Ticket.objects.filter(status=Status.IN_PROGRESS).count()
            data['total_closed'] = Ticket.objects.filter(status=Status.CLOSED).count()

            # Departman özeti
            from departments.models import Department
            dept_summary = Department.objects.annotate(
                open_count=Count('tickets', filter=Q(tickets__status=Status.OPEN)),
                total_count=Count('tickets'),
            ).order_by('-open_count')

            data['dept_summary'] = [
                {
                    'id': d.id,
                    'name': d.name,
                    'open_count': d.open_count,
                    'total_count': d.total_count,
                }
                for d in dept_summary
            ]

            data['recent_tickets'] = TicketListSerializer(
                Ticket.objects.select_related('sender', 'department', 'assigned_to', 'category')[:5],
                many=True,
            ).data

        # Son bildirimler (tüm roller için)
        data['recent_notifications'] = NotificationSerializer(
            Notification.objects.filter(
                recipient=user, is_read=False,
            ).select_related('ticket')[:5],
            many=True,
        ).data

        return Response(data)
