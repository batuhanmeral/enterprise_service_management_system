from django.urls import path

from . import api_views
# Export fonksiyonları mevcut views'dan (dosya döndürürler)
from .views import export_csv, export_excel, export_pdf

urlpatterns = [
    # Rapor dashboard — JSON istatistikler
    path('dashboard/', api_views.ReportDashboardAPIView.as_view(), name='api_report_dashboard'),
    # Dosya dışa aktarımları (mevcut SSR view'lar — dosya döndürürler)
    path('export/csv/', export_csv, name='api_export_csv'),
    path('export/excel/', export_excel, name='api_export_excel'),
    path('export/pdf/', export_pdf, name='api_export_pdf'),
]
