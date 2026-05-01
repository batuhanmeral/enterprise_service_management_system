from django.conf import settings
from django.db import models


# Rapor türlerini tanımlayan enumeration sınıfı
class ReportType(models.TextChoices):
    DEPARTMENT_PERFORMANCE = 'DEPARTMENT_PERFORMANCE', 'Departman Performansı'
    PERSONNEL_WORKLOAD = 'PERSONNEL_WORKLOAD', 'Personel İş Yükü'
    TICKET_SUMMARY = 'TICKET_SUMMARY', 'Bilet Özeti'
    CATEGORY_ANALYSIS = 'CATEGORY_ANALYSIS', 'Kategori Analizi'


# Oluşturulan raporları saklayan model
class Report(models.Model):

    # Raporun başlığı
    title = models.CharField(
        max_length=200,
        verbose_name='Rapor Başlığı',
    )

    # Raporun türü
    report_type = models.CharField(
        max_length=30,
        choices=ReportType.choices,
        verbose_name='Rapor Türü',
    )

    # Raporu oluşturan kullanıcı
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,  # Kullanıcı silinse bile rapor sistemde kalır
        null=True,
        related_name='reports',
        verbose_name='Oluşturan',
    )

    # Rapor belirli bir departmana ait olabilir (opsiyonel)
    department = models.ForeignKey(
        'departments.Department',
        on_delete=models.SET_NULL,  # Departman silinse bile rapor sistemde kalır
        null=True,
        blank=True,
        related_name='reports',
        verbose_name='Departman',
    )

    # Rapor tarih aralığı — başlangıç
    date_from = models.DateField(
        null=True,
        blank=True,
        verbose_name='Başlangıç Tarihi',
    )

    # Rapor tarih aralığı — bitiş
    date_to = models.DateField(
        null=True,
        blank=True,
        verbose_name='Bitiş Tarihi',
    )

    # Rapor verileri JSON snapshot olarak saklanır
    summary_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Özet Veriler',
    )

    # Dışa aktarılan rapor dosyası (PDF/Excel)
    file = models.FileField(
        upload_to='reports/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Rapor Dosyası',
    )

    # Raporun oluşturulma tarihi
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Oluşturulma Tarihi',
    )

    # Modelin admin paneli ve veritabanı davranışlarını belirleyen meta-veri sınıfı
    class Meta:
        verbose_name = 'Rapor'
        verbose_name_plural = 'Raporlar'
        ordering = ['-created_at']

    # Model objesinin sistemde metin olarak nasıl temsil edileceğini belirleyen fonksiyon
    def __str__(self):
        return f"{self.title} ({self.get_report_type_display()})"
