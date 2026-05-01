from rest_framework import serializers

from .models import User, Role


# Temel kullanıcı bilgileri — liste ve nested referanslarda kullanılır
class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'full_name',
            'email', 'phone', 'role', 'role_display',
            'department', 'department_name', 'is_active',
        ]
        read_only_fields = ['id', 'username']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


# Kısa kullanıcı referansı — bilet/bildirim nested alanlarında kullanılır
class UserShortSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


# Kullanıcı detay — bilet istatistikleri dahil
class UserDetailSerializer(UserSerializer):
    sent_tickets_count = serializers.IntegerField(read_only=True)
    assigned_tickets_count = serializers.IntegerField(read_only=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + [
            'sent_tickets_count', 'assigned_tickets_count', 'date_joined',
        ]


# Admin tarafından kullanıcı oluşturma
class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'phone', 'role', 'department', 'password',
        ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


# Admin tarafından kullanıcı güncelleme (şifresiz)
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'phone', 'role', 'department', 'is_active',
        ]


# Giriş (login) serializer'ı
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


# Kayıt (register) serializer'ı
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'password', 'password_confirm']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Şifreler eşleşmiyor.'})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        # Hesap pasif oluşturulur — admin onayı gerekir
        user.is_active = False
        user.role = Role.EMPLOYEE
        user.save()
        return user


# Profil güncelleme serializer'ı
class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
