from rest_framework import serializers

from identity.serializers import UserShortSerializer
from .models import Department, Category


# Kategori serializer'ı
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'department', 'name', 'description']
        read_only_fields = ['id', 'department']


# Departman listesi serializer'ı
class DepartmentSerializer(serializers.ModelSerializer):
    manager_detail = UserShortSerializer(source='manager', read_only=True)

    class Meta:
        model = Department
        fields = ['id', 'name', 'description', 'manager', 'manager_detail', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


# Departman detay — kategoriler, personel ve istatistikler dahil
class DepartmentDetailSerializer(DepartmentSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    personnel = UserShortSerializer(many=True, read_only=True)

    class Meta(DepartmentSerializer.Meta):
        fields = DepartmentSerializer.Meta.fields + ['categories', 'personnel']
