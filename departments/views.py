from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib import messages

from identity.models import User, Role
from identity.views import AdminRequiredMixin, ManagerOrAdminRequiredMixin

from .models import Department, Category


# Departman formu — yönetici alanı sadece atanmamış MANAGER rolündeki kullanıcılarla sınırlı
class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'description', 'manager']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Sadece MANAGER rolündeki ve departmanı olmayan kullanıcılar atanabilir.
        # Güncellemede mevcut yönetici listede kalmalı (departmanı zaten dolu olsa bile).
        eligible = User.objects.filter(
            role=Role.MANAGER,
            department__isnull=True,
            is_active=True,
        )
        instance = kwargs.get('instance') or getattr(self, 'instance', None)
        if instance and instance.pk and instance.manager_id:
            eligible = User.objects.filter(
                Q(pk=instance.manager_id)
                | Q(role=Role.MANAGER, department__isnull=True, is_active=True)
            )
        self.fields['manager'].queryset = eligible.distinct().order_by('first_name', 'last_name', 'username')
        self.fields['manager'].empty_label = '— Yönetici seçin (opsiyonel) —'


# Departman listeleme
class DepartmentListView(LoginRequiredMixin, ListView):
    model = Department
    template_name = 'departments/department_list.html'
    context_object_name = 'departments'


# Departman detay — kategoriler ve personel bilgisi ile birlikte
class DepartmentDetailView(LoginRequiredMixin, DetailView):
    model = Department
    template_name = 'departments/department_detail.html'
    context_object_name = 'department'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = self.object.categories.all()
        context['personnel'] = self.object.personnel.all()
        # Atanabilir personel: AGENT rolünde, departmanı boş, aktif
        context['available_personnel'] = User.objects.filter(
            role=Role.AGENT,
            department__isnull=True,
            is_active=True,
        ).order_by('first_name', 'last_name', 'username')
        return context


# Yeni departman oluşturma — Sadece ADMIN
class DepartmentCreateView(AdminRequiredMixin, CreateView):
    model = Department
    template_name = 'departments/department_form.html'
    form_class = DepartmentForm
    success_url = reverse_lazy('departments:department_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Atanan yöneticiyi bu departmana bağla — eligible havuzunda tekrar listelenmesin
        if self.object.manager_id and self.object.manager.department_id != self.object.pk:
            self.object.manager.department = self.object
            self.object.manager.save(update_fields=['department'])
        messages.success(self.request, f'"{self.object.name}" departmanı başarıyla oluşturuldu.')
        return response


# Departman güncelleme — Sadece ADMIN
class DepartmentUpdateView(AdminRequiredMixin, UpdateView):
    model = Department
    template_name = 'departments/department_form.html'
    form_class = DepartmentForm

    def get_success_url(self):
        return reverse_lazy('departments:department_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        # Yönetici değiştiyse: yeni yöneticiyi bu departmana bağla, eski yöneticinin departmanını boşalt
        old_manager_id = None
        if self.object.pk:
            old_manager_id = Department.objects.filter(pk=self.object.pk).values_list('manager_id', flat=True).first()
        response = super().form_valid(form)
        new_manager = self.object.manager
        if old_manager_id and old_manager_id != (new_manager.pk if new_manager else None):
            User.objects.filter(pk=old_manager_id, department=self.object).update(department=None)
        if new_manager and new_manager.department_id != self.object.pk:
            new_manager.department = self.object
            new_manager.save(update_fields=['department'])
        messages.success(self.request, f'"{self.object.name}" departmanı başarıyla güncellendi.')
        return response


# Departman silme — Sadece ADMIN
class DepartmentDeleteView(AdminRequiredMixin, DeleteView):
    model = Department
    template_name = 'departments/department_confirm_delete.html'
    context_object_name = 'department'
    success_url = reverse_lazy('departments:department_list')

    def form_valid(self, form):
        department_name = self.object.name
        response = super().form_valid(form)
        messages.success(self.request, f'"{department_name}" departmanı başarıyla silindi.')
        return response


# Kategori CRUD (departman bağlamında)

# Kategori oluşturma — Manager veya Admin (departmana bağlı)
class CategoryCreateView(ManagerOrAdminRequiredMixin, CreateView):
    model = Category
    template_name = 'departments/category_form.html'
    fields = ['name', 'description']

    def form_valid(self, form):
        form.instance.department_id = self.kwargs['dept_pk']
        response = super().form_valid(form)
        messages.success(self.request, f'"{self.object.name}" kategorisi başarıyla oluşturuldu.')
        return response

    def get_success_url(self):
        return reverse_lazy('departments:department_detail', kwargs={'pk': self.kwargs['dept_pk']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.shortcuts import get_object_or_404
        context['department'] = get_object_or_404(Department, pk=self.kwargs['dept_pk'])
        return context


# Kategori güncelleme — Manager veya Admin
class CategoryUpdateView(ManagerOrAdminRequiredMixin, UpdateView):
    model = Category
    template_name = 'departments/category_form.html'
    fields = ['name', 'description']

    def get_success_url(self):
        return reverse_lazy('departments:department_detail', kwargs={'pk': self.object.department_id})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'"{self.object.name}" kategorisi başarıyla güncellendi.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['department'] = self.object.department
        return context


# Kategori silme — Manager veya Admin
class CategoryDeleteView(ManagerOrAdminRequiredMixin, DeleteView):
    model = Category
    template_name = 'departments/category_confirm_delete.html'
    context_object_name = 'category'

    def get_success_url(self):
        return reverse_lazy('departments:department_detail', kwargs={'pk': self.object.department_id})

    def form_valid(self, form):
        category_name = self.object.name
        response = super().form_valid(form)
        messages.success(self.request, f'"{category_name}" kategorisi başarıyla silindi.')
        return response


# AJAX endpoint — departmana ait kategorileri JSON olarak döndürür
@login_required
def department_categories_api(request, pk):
    categories = Category.objects.filter(department_id=pk).values('id', 'name')
    return JsonResponse(list(categories), safe=False)


# Departmana personel ekleme — Admin veya departmanın yöneticisi
@login_required
def department_add_personnel(request, pk):
    from django.shortcuts import get_object_or_404, redirect

    if request.method != 'POST':
        return HttpResponseForbidden('Sadece POST istekleri kabul edilir.')

    department = get_object_or_404(Department, pk=pk)

    # Yetki: ADMIN her departmana, MANAGER sadece kendi departmanına ekleyebilir
    is_admin = request.user.role == Role.ADMIN
    is_dept_manager = (
        request.user.role == Role.MANAGER
        and request.user.department_id == department.pk
    )
    if not (is_admin or is_dept_manager):
        return HttpResponseForbidden('Bu departmana personel ekleme yetkiniz yok.')

    user_id = request.POST.get('user_id')
    if not user_id:
        messages.error(request, 'Lütfen bir personel seçin.')
        return redirect('departments:department_detail', pk=pk)

    try:
        user = User.objects.get(
            pk=user_id,
            role=Role.AGENT,
            department__isnull=True,
            is_active=True,
        )
    except User.DoesNotExist:
        messages.error(request, 'Seçilen kullanıcı uygun değil veya zaten bir departmana atanmış.')
        return redirect('departments:department_detail', pk=pk)

    user.department = department
    user.save(update_fields=['department'])
    messages.success(
        request,
        f'"{user.get_full_name() or user.username}" "{department.name}" departmanına eklendi.',
    )
    return redirect('departments:department_detail', pk=pk)
