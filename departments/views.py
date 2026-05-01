from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib import messages

from .models import Department, Category


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
        return context


# Yeni departman oluşturma
class DepartmentCreateView(LoginRequiredMixin, CreateView):
    model = Department
    template_name = 'departments/department_form.html'
    fields = ['name', 'description', 'manager']
    success_url = reverse_lazy('departments:department_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'"{self.object.name}" departmanı başarıyla oluşturuldu.')
        return response


# Departman güncelleme
class DepartmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Department
    template_name = 'departments/department_form.html'
    fields = ['name', 'description', 'manager']

    def get_success_url(self):
        return reverse_lazy('departments:department_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'"{self.object.name}" departmanı başarıyla güncellendi.')
        return response


# Departman silme
class DepartmentDeleteView(LoginRequiredMixin, DeleteView):
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

# Kategori oluşturma — departmana bağlı
class CategoryCreateView(LoginRequiredMixin, CreateView):
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


# Kategori güncelleme
class CategoryUpdateView(LoginRequiredMixin, UpdateView):
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


# Kategori silme
class CategoryDeleteView(LoginRequiredMixin, DeleteView):
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
