from django.contrib.auth import authenticate
from django.db.models import Count

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.generics import (
    ListAPIView, CreateAPIView, RetrieveAPIView, UpdateAPIView,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.permissions import IsAdmin
from .models import User, Role
from .serializers import (
    UserSerializer, UserDetailSerializer, UserCreateSerializer,
    UserUpdateSerializer, LoginSerializer, RegisterSerializer,
    ProfileUpdateSerializer,
)


# Kimlik Doğrulama

# Kullanıcı girişi — Token döndürür
class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data,
            })

        # Pasif hesap kontrolü — daha bilgilendirici hata mesajı
        try:
            existing = User.objects.get(username=username)
            if not existing.is_active:
                return Response(
                    {'detail': 'Hesabınız henüz admin tarafından onaylanmamıştır.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except User.DoesNotExist:
            pass

        return Response(
            {'detail': 'Geçersiz kullanıcı adı veya şifre.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )


# Kullanıcı çıkışı — Token'ı siler
class LogoutAPIView(APIView):
    def post(self, request):
        # Kullanıcının token'ını sil
        Token.objects.filter(user=request.user).delete()
        return Response({'detail': 'Başarıyla çıkış yapıldı.'})


# Kayıt (Register) — Admin Onaylı

# Yeni kullanıcı kaydı — hesap pasif oluşturulur
class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'detail': 'Kayıt başarılı! Hesabınız admin onayına gönderildi.'},
            status=status.HTTP_201_CREATED,
        )


# Profil

# Profil görüntüleme ve güncelleme
class ProfileAPIView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def put(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


# Profil silme (soft delete — hesabı deaktif eder ve token'ı siler)
class ProfileDeleteAPIView(APIView):
    def post(self, request):
        user = request.user
        user.is_active = False
        user.save(update_fields=['is_active'])
        Token.objects.filter(user=user).delete()
        return Response({'detail': 'Hesabınız başarıyla silindi.'})


# Admin: Kullanıcı Yönetimi

# Kullanıcı listesi — Sadece ADMIN
class UserListAPIView(ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    queryset = User.objects.all()

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Onay bekleyen kullanıcı sayısını ekle
        response.data['pending_count'] = User.objects.filter(is_active=False).count()
        return response


# Kullanıcı oluşturma — Sadece ADMIN
class UserCreateAPIView(CreateAPIView):
    serializer_class = UserCreateSerializer
    permission_classes = [IsAdmin]


# Kullanıcı detay — Sadece ADMIN
class UserDetailAPIView(RetrieveAPIView):
    serializer_class = UserDetailSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        return User.objects.annotate(
            sent_tickets_count=Count('sent_tickets'),
            assigned_tickets_count=Count('assigned_tickets'),
        )


# Kullanıcı güncelleme — Sadece ADMIN
class UserUpdateAPIView(UpdateAPIView):
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAdmin]
    queryset = User.objects.all()


# Kullanıcı silme (soft delete) — Sadece ADMIN
class UserDeleteAPIView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        user = User.objects.filter(pk=pk).first()
        if not user:
            return Response(
                {'detail': 'Kullanıcı bulunamadı.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Admin kendini silemez
        if user == request.user:
            return Response(
                {'detail': 'Kendi hesabınızı silemezsiniz.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response({'detail': f'"{user.username}" kullanıcısı deaktif edildi.'})


# Kullanıcı onaylama — Sadece ADMIN (pasif hesabı aktif yapar)
class UserApproveAPIView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        user = User.objects.filter(pk=pk).first()
        if not user:
            return Response(
                {'detail': 'Kullanıcı bulunamadı.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response({'detail': f'"{user.username}" kullanıcısı onaylandı ve aktif edildi.'})
