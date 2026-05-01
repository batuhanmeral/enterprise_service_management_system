from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, CreateView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.db.models import Q

from .models import Ticket, Status, Priority, TicketHistory
from notifications.models import Notification
from identity.models import Role


# Audit log yardımcı fonksiyonu
def log_ticket_action(ticket, actor, action):
    TicketHistory.objects.create(ticket=ticket, actor=actor, action=action)


# Bilet listeleme - Rol bazlı filtreleme + sıralama
class TicketListView(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = 'tickets/ticket_list.html'
    context_object_name = 'tickets'
    paginate_by = 20

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

        # Durum filtresi (query string: ?status=OPEN)
        status_filter = self.request.GET.get('status')
        if status_filter and status_filter in dict(Status.choices):
            qs = qs.filter(status=status_filter)

        # Öncelik filtresi (?priority=HIGH)
        priority_filter = self.request.GET.get('priority')
        if priority_filter and priority_filter in dict(Priority.choices):
            qs = qs.filter(priority=priority_filter)

        # Sıralama (?sort=priority / ?sort=status / ?sort=created_at)
        sort = self.request.GET.get('sort', '-created_at')
        allowed_sorts = {
            'created_at': 'created_at',
            '-created_at': '-created_at',
            'priority': '-priority',
            'status': 'status',
            'subject': 'subject',
        }
        qs = qs.order_by(allowed_sorts.get(sort, '-created_at'))

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_role'] = self.request.user.role
        context['status_choices'] = Status.choices
        context['priority_choices'] = Priority.choices
        context['current_status'] = self.request.GET.get('status', '')
        context['current_priority'] = self.request.GET.get('priority', '')
        context['current_sort'] = self.request.GET.get('sort', '-created_at')
        return context


# Yeni bilet oluşturma - sender otomatik atanır
class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    template_name = 'tickets/ticket_form.html'
    fields = ['subject', 'message', 'department', 'category', 'priority', 'attachment']
    success_url = reverse_lazy('tickets:ticket_list')

    def form_valid(self, form):
        form.instance.sender = self.request.user
        form.instance.status = Status.OPEN
        response = super().form_valid(form)

        # Audit log
        log_ticket_action(self.object, self.request.user, 'Bilet oluşturuldu.')

        messages.success(
            self.request,
            f'Talebiniz başarıyla oluşturuldu. (Bilet #{self.object.pk})',
        )
        return response


# Bilet detay - Rol bazlı erişim kontrolü + geçmiş
class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Ticket
    template_name = 'tickets/ticket_detail.html'
    context_object_name = 'ticket'

    def get_queryset(self):
        user = self.request.user
        qs = Ticket.objects.select_related(
            'sender', 'assigned_to', 'department', 'category',
        )

        if user.role == Role.ADMIN:
            return qs
        elif user.role in (Role.AGENT, Role.MANAGER):
            return qs.filter(
                Q(department=user.department) | Q(sender=user)
            )
        else:
            return qs.filter(sender=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['history'] = self.object.history.select_related('actor').all()
        return context


# Talep üstlenme - Personel bileti üzerine alır (OPEN -> IN_PROGRESS)
@login_required
def ticket_take_view(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden('Sadece POST istekleri kabul edilir.')

    user = request.user

    if user.role not in (Role.AGENT, Role.MANAGER):
        return HttpResponseForbidden('Bu işlem için yetkiniz bulunmamaktadır.')

    ticket = get_object_or_404(Ticket, pk=pk)

    if ticket.department != user.department:
        return HttpResponseForbidden('Bu bilet sizin departmanınıza ait değildir.')

    if ticket.status != Status.OPEN:
        messages.warning(request, 'Bu bilet zaten işlemde veya kapalı durumda.')
        return redirect('tickets:ticket_detail', pk=ticket.pk)

    ticket.take_into_process(personnel=user)
    log_ticket_action(ticket, user, f'{user.get_full_name() or user.username} bileti üstlendi.')

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

    messages.success(request, f'Bilet #{ticket.pk} başarıyla üstlenildi.')
    return redirect('tickets:ticket_detail', pk=ticket.pk)


# Talep kapatma - Atanan personel bileti kapatır (IN_PROGRESS -> CLOSED)
@login_required
def ticket_close_view(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden('Sadece POST istekleri kabul edilir.')

    user = request.user
    ticket = get_object_or_404(Ticket, pk=pk)

    is_assigned = (ticket.assigned_to == user)
    is_admin = (user.role == Role.ADMIN)

    if not (is_assigned or is_admin):
        return HttpResponseForbidden(
            'Sadece bileti üstlenen personel veya Admin kapatabilir.'
        )

    if ticket.status != Status.IN_PROGRESS:
        messages.warning(request, 'Sadece "İşlemde" durumundaki biletler kapatılabilir.')
        return redirect('tickets:ticket_detail', pk=ticket.pk)

    resolution_note = request.POST.get('resolution_note', '')
    ticket.close(resolution_note=resolution_note)
    log_ticket_action(ticket, user, f'Bilet kapatıldı. Çözüm: {resolution_note[:100]}')

    if ticket.sender:
        Notification.objects.create(
            recipient=ticket.sender,
            ticket=ticket,
            message=(
                f'Talebiniz "{ticket.subject}" (#{ticket.pk}) '
                f'çözülmüş ve kapatılmıştır.'
            ),
        )

    messages.success(request, f'Bilet #{ticket.pk} başarıyla kapatıldı.')
    return redirect('tickets:ticket_detail', pk=ticket.pk)


# Bilet transfer -- Başka departmana aktarma (AGENT/MANAGER/ADMIN)
@login_required
def ticket_transfer_view(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    user = request.user

    if user.role not in (Role.AGENT, Role.MANAGER, Role.ADMIN):
        return HttpResponseForbidden('Bu işlem için yetkiniz bulunmamaktadır.')

    if user.role in (Role.AGENT, Role.MANAGER):
        if ticket.department != user.department:
            return HttpResponseForbidden('Bu bilet sizin departmanınıza ait değildir.')

    if ticket.status == Status.CLOSED:
        messages.warning(request, 'Kapalı biletler transfer edilemez.')
        return redirect('tickets:ticket_detail', pk=ticket.pk)

    if request.method == 'GET':
        from departments.models import Department
        departments = Department.objects.exclude(pk=ticket.department_id)
        return render(request, 'tickets/ticket_transfer.html', {
            'ticket': ticket,
            'departments': departments,
        })

    from departments.models import Department, Category
    new_dept_id = request.POST.get('department')
    new_cat_id = request.POST.get('category') or None

    new_department = get_object_or_404(Department, pk=new_dept_id)
    new_category = None
    if new_cat_id:
        new_category = get_object_or_404(Category, pk=new_cat_id, department=new_department)

    old_department = ticket.department
    ticket.transfer(new_department, new_category)
    log_ticket_action(
        ticket, user,
        f'Bilet {old_department.name if old_department else "?"} -> {new_department.name} departmanına transfer edildi.',
    )

    if ticket.sender:
        Notification.objects.create(
            recipient=ticket.sender,
            ticket=ticket,
            message=(
                f'Talebiniz "{ticket.subject}" (#{ticket.pk}) '
                f'{new_department.name} departmanına transfer edilmiştir.'
            ),
        )

    if ticket.assigned_to and ticket.assigned_to != user:
        Notification.objects.create(
            recipient=ticket.assigned_to,
            ticket=ticket,
            message=(
                f'Üstlendiğiniz bilet "{ticket.subject}" (#{ticket.pk}) '
                f'{new_department.name} departmanına transfer edildi.'
            ),
        )

    messages.success(
        request,
        f'Bilet #{ticket.pk} "{new_department.name}" departmanına transfer edildi.',
    )

    # Eğer kullanıcı Admin değilse ve bilet sahibi değilse, transfer sonrası bileti göremez
    if user.role != Role.ADMIN and ticket.sender != user:
        return redirect('tickets:ticket_list')

    return redirect('tickets:ticket_detail', pk=ticket.pk)


# Bilet güncelleme — Sadece talep sahibi (OPEN durumdayken)
class TicketUpdateView(LoginRequiredMixin, UpdateView):
    model = Ticket
    template_name = 'tickets/ticket_form.html'
    fields = ['subject', 'message', 'department', 'category', 'priority', 'attachment']

    def get_queryset(self):
        user = self.request.user
        qs = Ticket.objects.select_related('department', 'category')

        if user.role == Role.ADMIN:
            return qs
        return qs.filter(sender=user, status=Status.OPEN)

    def get_success_url(self):
        return reverse_lazy('tickets:ticket_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        log_ticket_action(self.object, self.request.user, 'Bilet güncellendi.')
        messages.success(self.request, f'Bilet #{self.object.pk} başarıyla güncellendi.')
        return response


# Bilet silme — Talep sahibi (OPEN), ilgili Manager veya Admin
@login_required
def ticket_delete_view(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden('Sadece POST istekleri kabul edilir.')

    ticket = get_object_or_404(Ticket, pk=pk)
    user = request.user

    is_sender_open = (ticket.sender == user and ticket.status == Status.OPEN)
    is_admin = (user.role == Role.ADMIN)
    is_dept_manager = (
        user.role == Role.MANAGER
        and ticket.department == user.department
    )

    if not (is_sender_open or is_admin or is_dept_manager):
        return HttpResponseForbidden(
            'Sadece talep sahibi (açık biletler), ilgili yönetici veya Admin silebilir.'
        )

    ticket_pk = ticket.pk
    ticket.delete()

    messages.success(request, f'Bilet #{ticket_pk} başarıyla silindi.')
    return redirect('tickets:ticket_list')
