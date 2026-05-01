from rest_framework.generics import (
    ListCreateAPIView, RetrieveUpdateDestroyAPIView,
    ListAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated

from .models import Department, Category
from .serializers import (
    DepartmentSerializer, DepartmentDetailSerializer, CategorySerializer,
)


# Departman CRUD

# Departman listeleme ve oluşturma
class DepartmentListCreateAPIView(ListCreateAPIView):
    queryset = Department.objects.select_related('manager')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DepartmentSerializer
        return DepartmentSerializer


# Departman detay, güncelleme ve silme
class DepartmentDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Department.objects.select_related('manager').prefetch_related('categories', 'personnel')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return DepartmentDetailSerializer
        return DepartmentSerializer


# Kategori CRUD (departman bağlamında)

# Departmana ait kategorileri listeleme ve oluşturma
class CategoryListCreateAPIView(ListCreateAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(department_id=self.kwargs['dept_pk'])

    def perform_create(self, serializer):
        # department_id URL'den alınır
        serializer.save(department_id=self.kwargs['dept_pk'])


# Kategori güncelleme ve silme
class CategoryDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    queryset = Category.objects.all()
