from django.contrib import admin

from .models import Report, ReportType


# Rapor modelini admin panelinde yönetmek için sınıf
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):

    # Admin panelinde rapor listesinde gösterilecek alanlar
    list_display = (
        'id',
        'title',
        'report_type',
        'generated_by',
        'department',
        'date_from',
        'date_to',
        'has_file',
        'created_at',
    )

    # Admin panelinde rapor listesinde filtreleme seçenekleri
    list_filter = (
        'report_type',
        'department',
        'created_at',
    )

    # Admin panelinde rapor listesinde arama yapılacak alanlar
    search_fields = (
        'title',
        'generated_by__username',
        'generated_by__first_name',
        'generated_by__last_name',
        'department__name',
    )

    # Admin panelinde rapor sayfasında salt okunur alanlar
    readonly_fields = (
        'created_at',
    )

    # Admin panelinde rapor detay sayfası alan grupları
    fieldsets = (
        ('Rapor Bilgileri', {
            'fields': ('title', 'report_type', 'generated_by', 'department'),
        }),
        ('Tarih Aralığı', {
            'fields': ('date_from', 'date_to'),
        }),
        ('Veriler', {
            'fields': ('summary_data', 'file'),
        }),
        ('Zaman Bilgileri', {
            'fields': ('created_at',),
        }),
    )

    # Admin panelinde rapor listesinde ilişkili alanları önbelleğe al
    list_select_related = (
        'generated_by',
        'department',
    )

    # Admin panelinde sayfa başına gösterilecek rapor sayısı
    list_per_page = 25

    # Admin panelinde rapor listesinde tarih hiyerarşisi
    date_hierarchy = 'created_at'

    # Rapor dosyası var mı gösterimi
    @admin.display(description='Dosya', boolean=True)
    def has_file(self, obj):
        return bool(obj.file)
