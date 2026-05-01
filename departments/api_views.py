from rest_framework.generics import (
    ListCreateAPIView, RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS

from config.permissions import IsAdmin, IsManagerOrAdmin
from .models import Department, Category
from .serializers import (
    DepartmentSerializer, DepartmentDetailSerializer, CategorySerializer,
)


# Departman CRUD

# Departman listeleme (herkes) ve oluşturma (sadece Admin)
class DepartmentListCreateAPIView(ListCreateAPIView):
    queryset = Department.objects.select_related('manager')

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        return [IsAdmin()]

    def get_serializer_class(self):
        return DepartmentSerializer


# Departman detay (herkes), güncelleme ve silme (sadece Admin)
class DepartmentDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Department.objects.select_related('manager').prefetch_related('categories', 'personnel')

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        return [IsAdmin()]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return DepartmentDetailSerializer
        return DepartmentSerializer


# Kategori CRUD (departman bağlamında)

# Departmana ait kategorileri listeleme (herkes) ve oluşturma (Manager veya Admin)
class CategoryListCreateAPIView(ListCreateAPIView):
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        return [IsManagerOrAdmin()]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Category.objects.none()
        return Category.objects.filter(department_id=self.kwargs['dept_pk'])

    def perform_create(self, serializer):
        # department_id URL'den alınır
        serializer.save(department_id=self.kwargs['dept_pk'])


# Kategori detay (herkes), güncelleme ve silme (Manager veya Admin)
class CategoryDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        return [IsManagerOrAdmin()]
