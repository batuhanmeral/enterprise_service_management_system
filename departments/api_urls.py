from django.urls import path

from . import api_views

urlpatterns = [
    # Departman listeleme ve oluşturma
    path('', api_views.DepartmentListCreateAPIView.as_view(), name='api_department_list'),
    # Departman detay, güncelleme ve silme
    path('<int:pk>/', api_views.DepartmentDetailAPIView.as_view(), name='api_department_detail'),
    # Departmana ait kategoriler — listeleme ve oluşturma
    path('<int:dept_pk>/categories/', api_views.CategoryListCreateAPIView.as_view(), name='api_category_list'),
    # Kategori detay, güncelleme ve silme
    path('categories/<int:pk>/', api_views.CategoryDetailAPIView.as_view(), name='api_category_detail'),
]
