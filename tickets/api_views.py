from django.shortcuts import get_object_or_404
from django.db.models import Q

from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from departments.models import Department, Category
from identity.models import Role
from notifications.models import Notification

from .models import Ticket, Status as TicketStatus, Priority, TicketHistory
from .serializers import (
    TicketListSerializer, TicketDetailSerializer,
    TicketCreateSerializer, TicketUpdateSerializer,
    TicketCloseSerializer, TicketTransferSerializer,
)


# Audit log yardımcı fonksiyonu
def log_ticket_action(ticket, actor, action):
    TicketHistory.objects.create(ticket=ticket, actor=actor, action=action)


# Bilet Listeleme ve Oluşturma


class TicketListCreateAPIView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TicketCreateSerializer
        return TicketListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Ticket.objects.select_related(
            'sender', 'assigned_to', 'department', 'category',
        )

        # Rol bazlı filtreleme
        if user.role == Role.ADMIN:
            pass  # Tüm biletler
        elif user.role in (Role.AGENT, Role.MANAGER):
            qs = qs.filter(department=user.department)
        else:
            qs = qs.filter(sender=user)

        # Durum filtresi (?status=OPEN)
        status_filter = self.request.query_params.get('status')
        if status_filter and status_filter in dict(TicketStatus.choices):
            qs = qs.filter(status=status_filter)

        # Öncelik filtresi (?priority=HIGH)
        priority_filter = self.request.query_params.get('priority')
        if priority_filter and priority_filter in dict(Priority.choices):
            qs = qs.filter(priority=priority_filter)

        # Sıralama (?sort=priority / status / created_at / subject)
        sort = self.request.query_params.get('sort', '-created_at')
        allowed_sorts = {
            'created_at': 'created_at',
            '-created_at': '-created_at',
            'priority': '-priority',
            'status': 'status',
            'subject': 'subject',
        }
        qs = qs.order_by(allowed_sorts.get(sort, '-created_at'))

        return qs

    def perform_create(self, serializer):
        # sender otomatik atanır, durum OPEN
        ticket = serializer.save(sender=self.request.user, status=TicketStatus.OPEN)
        log_ticket_action(ticket, self.request.user, 'Bilet oluşturuldu.')


# Bilet Detay, Güncelleme ve Silme


class TicketDetailAPIView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return TicketDetailSerializer
        return TicketUpdateSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Ticket.objects.select_related(
            'sender', 'assigned_to', 'department', 'category',
        ).prefetch_related('history__actor')

        if user.role == Role.ADMIN:
            return qs
        elif user.role in (Role.AGENT, Role.MANAGER):
            return qs.filter(
                Q(department=user.department) | Q(sender=user)
            )
        else:
            return qs.filter(sender=user)

    def perform_update(self, serializer):
        user = self.request.user
        ticket = self.get_object()

        # Güncelleme yetkisi: sender (OPEN) veya Admin
        if user.role != Role.ADMIN:
            if ticket.sender != user or ticket.status != TicketStatus.OPEN:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Sadece açık durumdaki kendi biletlerinizi güncelleyebilirsiniz.')

        serializer.save()
        log_ticket_action(ticket, user, 'Bilet güncellendi.')

    def perform_destroy(self, instance):
        user = self.request.user

        is_sender_open = (instance.sender == user and instance.status == TicketStatus.OPEN)
        is_admin = (user.role == Role.ADMIN)
        is_dept_manager = (
            user.role == Role.MANAGER
            and instance.department == user.department
        )

        if not (is_sender_open or is_admin or is_dept_manager):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                'Sadece talep sahibi (açık biletler), ilgili yönetici veya Admin silebilir.'
            )

        instance.delete()


# Bilet Üstlenme (OPEN → IN_PROGRESS)


class TicketTakeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user

        if user.role not in (Role.AGENT, Role.MANAGER):
            return Response(
                {'detail': 'Bu işlem için yetkiniz bulunmamaktadır.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        ticket = get_object_or_404(Ticket, pk=pk)

        if ticket.department != user.department:
            return Response(
                {'detail': 'Bu bilet sizin departmanınıza ait değildir.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if ticket.status != TicketStatus.OPEN:
            return Response(
                {'detail': 'Bu bilet zaten işlemde veya kapalı durumda.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ticket.take_into_process(personnel=user)
        log_ticket_action(ticket, user, f'{user.get_full_name() or user.username} bileti üstlendi.')

        # Talep sahibine bildirim
        if ticket.sender:
            Notification.objects.create(
                recipient=ticket.sender,
                ticket=ticket,
                message=(
                    f'Talebiniz "{ticket.subject}" (#{ticket.pk}) '
                    f'{user.get_full_name() or user.username} tarafından '
                    f'işleme alınmıştır.'
                ),
            )

        return Response(TicketDetailSerializer(ticket).data)


# Bilet Kapatma (IN_PROGRESS → CLOSED)


class TicketCloseAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        ticket = get_object_or_404(Ticket, pk=pk)

        is_assigned = (ticket.assigned_to == user)
        is_admin = (user.role == Role.ADMIN)

        if not (is_assigned or is_admin):
            return Response(
                {'detail': 'Sadece bileti üstlenen personel veya Admin kapatabilir.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if ticket.status != TicketStatus.IN_PROGRESS:
            return Response(
                {'detail': 'Sadece "İşlemde" durumundaki biletler kapatılabilir.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TicketCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        resolution_note = serializer.validated_data['resolution_note']
        ticket.close(resolution_note=resolution_note)
        log_ticket_action(ticket, user, f'Bilet kapatıldı. Çözüm: {resolution_note[:100]}')

        # Talep sahibine bildirim
        if ticket.sender:
            Notification.objects.create(
                recipient=ticket.sender,
                ticket=ticket,
                message=(
                    f'Talebiniz "{ticket.subject}" (#{ticket.pk}) '
                    f'çözülmüş ve kapatılmıştır.'
                ),
            )

        return Response(TicketDetailSerializer(ticket).data)


# Bilet Transfer (Departmanlar arası aktarım)


class TicketTransferAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        ticket = get_object_or_404(Ticket, pk=pk)

        if user.role not in (Role.AGENT, Role.MANAGER, Role.ADMIN):
            return Response(
                {'detail': 'Bu işlem için yetkiniz bulunmamaktadır.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Agent/Manager sadece kendi departman biletlerini transfer edebilir
        if user.role in (Role.AGENT, Role.MANAGER):
            if ticket.department != user.department:
                return Response(
                    {'detail': 'Bu bilet sizin departmanınıza ait değildir.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        if ticket.status == TicketStatus.CLOSED:
            return Response(
                {'detail': 'Kapalı biletler transfer edilemez.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TicketTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_dept_id = serializer.validated_data['department']
        new_cat_id = serializer.validated_data.get('category')

        new_department = get_object_or_404(Department, pk=new_dept_id)
        new_category = None
        if new_cat_id:
            new_category = get_object_or_404(Category, pk=new_cat_id, department=new_department)

        old_department = ticket.department
        old_assigned = ticket.assigned_to

        ticket.transfer(new_department, new_category)
        log_ticket_action(
            ticket, user,
            f'Bilet {old_department.name if old_department else "?"} → {new_department.name} departmanına transfer edildi.',
        )

        # Talep sahibine bildirim
        if ticket.sender:
            Notification.objects.create(
                recipient=ticket.sender,
                ticket=ticket,
                message=(
                    f'Talebiniz "{ticket.subject}" (#{ticket.pk}) '
                    f'{new_department.name} departmanına transfer edilmiştir.'
                ),
            )

        # Eski atanan personele bildirim
        if old_assigned and old_assigned != user:
            Notification.objects.create(
                recipient=old_assigned,
                ticket=ticket,
                message=(
                    f'Üstlendiğiniz bilet "{ticket.subject}" (#{ticket.pk}) '
                    f'{new_department.name} departmanına transfer edildi.'
                ),
            )

        return Response(TicketDetailSerializer(ticket).data)
