from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import TemplateView, FormView, ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.http import HttpResponseForbidden
from django.contrib import messages
from django import forms

from .models import User, Role


# Kimlik Dogrulama


# Kullanıcı giriş formu
class LoginForm(forms.Form):
    username = forms.CharField(
        label='Kullanıcı Adı',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Kullanıcı adınızı girin',
        }),
    )
    password = forms.CharField(
        label='Şifre',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Şifrenizi girin',
        }),
    )


# Kullanıcı giriş görünümü
class LoginView(FormView):
    template_name = 'identity/login.html'
    form_class = LoginForm
    success_url = reverse_lazy('tickets:ticket_list')

    def form_valid(self, form):
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user = authenticate(self.request, username=username, password=password)

        if user is not None:
            login(self.request, user)
            messages.success(self.request, f'Hoş geldiniz, {user.get_full_name() or user.username}!')
            next_url = self.request.GET.get('next', self.get_success_url())
            return redirect(next_url)
        else:
            # Pasif hesap kontrolü — daha bilgilendirici mesaj
            try:
                existing = User.objects.get(username=username)
                if not existing.is_active:
                    messages.warning(
                        self.request,
                        'Hesabınız henüz admin tarafından onaylanmamıştır. '
                        'Lütfen onay sürecini bekleyin.',
                    )
                    return self.form_invalid(form)
            except User.DoesNotExist:
                pass
            messages.error(self.request, 'Geçersiz kullanıcı adı veya şifre.')
            return self.form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)


# Kullanıcı çıkış işlemi
def logout_view(request):
    logout(request)
    messages.info(request, 'Başarıyla çıkış yapıldı.')
    return redirect('identity:login')


# Kayıt (Register) — Admin Onaylı


# Kayıt formu
class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        label='Şifre',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Şifre belirleyin',
        }),
    )
    password_confirm = forms.CharField(
        label='Şifre Tekrar',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Şifrenizi tekrar girin',
        }),
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'role', 'department']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Şifreler eşleşmiyor.')
        return password_confirm

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        # Hesap pasif olarak oluşturulur — admin onayı gerekir
        user.is_active = False
        if commit:
            user.save()
        return user


# Kayıt view'ı — anonim kullanıcılar için
class RegisterView(FormView):
    template_name = 'identity/register.html'
    form_class = RegisterForm
    success_url = reverse_lazy('identity:login')

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request,
            'Kayıt başarılı! Hesabınız admin onayına gönderildi. '
            'Onaylandıktan sonra giriş yapabilirsiniz.',
        )
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('tickets:ticket_list')
        return super().dispatch(request, *args, **kwargs)


# Profil


# Kullanıcı profil görünümü
class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'identity/profile.html'


# Kullanıcı bilgilerini güncelleme
@login_required
def profile_update_view(request):
    if request.method != 'POST':
        return redirect('identity:profile')

    user = request.user
    user.first_name = request.POST.get('first_name', '').strip()
    user.last_name = request.POST.get('last_name', '').strip()
    user.email = request.POST.get('email', '').strip()
    user.phone = request.POST.get('phone', '').strip() or None
    user.save(update_fields=['first_name', 'last_name', 'email', 'phone'])

    messages.success(request, 'Profil bilgileriniz başarıyla güncellendi.')
    return redirect('identity:profile')


# Kullanıcı kendi hesabını siler (deaktif eder ve çıkış yapar)
@login_required
def profile_delete_view(request):
    if request.method != 'POST':
        return HttpResponseForbidden('Sadece POST istekleri kabul edilir.')

    user = request.user
    username = user.username

    # Hesabı deaktif et ve çıkış yap
    user.is_active = False
    user.save(update_fields=['is_active'])
    logout(request)

    messages.info(request, f'"{username}" hesabınız başarıyla silindi.')
    return redirect('identity:login')


# Admin/Yönetici: Kullanıcı Yönetimi


# Yetki kontrolü mixin — Sadece ADMIN rolü erişebilir
class AdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != Role.ADMIN:
            return HttpResponseForbidden('Bu sayfaya erişim yetkiniz bulunmamaktadır.')
        return super().dispatch(request, *args, **kwargs)


# Kullanıcı listesi — Sadece ADMIN
class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = 'identity/user_list.html'
    context_object_name = 'users'
    paginate_by = 25

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Onay bekleyen kullanıcı sayısı
        context['pending_count'] = User.objects.filter(is_active=False).count()
        return context


# Kullanıcı detay — Sadece ADMIN
class UserDetailView(AdminRequiredMixin, DetailView):
    model = User
    template_name = 'identity/user_detail.html'
    context_object_name = 'profile_user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = self.object
        context['sent_tickets_count'] = profile_user.sent_tickets.count()
        context['assigned_tickets_count'] = profile_user.assigned_tickets.count()
        return context


# Kullanıcı oluşturma formu (Admin tarafından)
class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label='Şifre',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Şifre belirleyin',
        }),
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'role', 'department']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


# Yeni kullanıcı oluşturma — Sadece ADMIN
class UserCreateView(AdminRequiredMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = 'identity/user_form.html'
    success_url = reverse_lazy('identity:user_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'"{self.object.username}" kullanıcısı başarıyla oluşturuldu.')
        return response


# Kullanıcı güncelleme formu (şifresiz)
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'role', 'department', 'is_active']


# Kullanıcı güncelleme — Sadece ADMIN
class UserUpdateView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'identity/user_form.html'
    context_object_name = 'profile_user'

    def get_success_url(self):
        return reverse_lazy('identity:user_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'"{self.object.username}" kullanıcısı başarıyla güncellendi.')
        return response


# Kullanıcı silme (deaktif) — Sadece ADMIN
@login_required
def user_delete_view(request, pk):
    if request.user.role != Role.ADMIN:
        return HttpResponseForbidden('Bu işlem için yetkiniz bulunmamaktadır.')

    if request.method != 'POST':
        return HttpResponseForbidden('Sadece POST istekleri kabul edilir.')

    user = get_object_or_404(User, pk=pk)

    # Admin kendini silemez
    if user == request.user:
        messages.warning(request, 'Kendi hesabınızı silemezsiniz.')
        return redirect('identity:user_detail', pk=pk)

    username = user.username
    user.is_active = False
    user.save(update_fields=['is_active'])

    messages.success(request, f'"{username}" kullanıcısı deaktif edildi.')
    return redirect('identity:user_list')


# Kullanıcı onaylama — Sadece ADMIN (pasif hesabı aktif yapar)
@login_required
def user_approve_view(request, pk):
    if request.user.role != Role.ADMIN:
        return HttpResponseForbidden('Bu işlem için yetkiniz bulunmamaktadır.')

    if request.method != 'POST':
        return HttpResponseForbidden('Sadece POST istekleri kabul edilir.')

    user = get_object_or_404(User, pk=pk)
    user.is_active = True
    user.save(update_fields=['is_active'])

    messages.success(request, f'"{user.username}" kullanıcısı onaylandı ve aktif edildi.')
    return redirect('identity:user_list')
