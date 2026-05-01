from rest_framework import serializers

from identity.serializers import UserShortSerializer
from .models import Ticket, TicketHistory


# Bilet geçmişi (audit log) serializer'ı
class TicketHistorySerializer(serializers.ModelSerializer):
    actor = UserShortSerializer(read_only=True)

    class Meta:
        model = TicketHistory
        fields = ['id', 'actor', 'action', 'created_at']


# Bilet listesi serializer'ı — kısa bilgiler
class TicketListSerializer(serializers.ModelSerializer):
    sender = UserShortSerializer(read_only=True)
    assigned_to = UserShortSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)

    class Meta:
        model = Ticket
        fields = [
            'id', 'subject', 'status', 'status_display',
            'priority', 'priority_display',
            'department', 'department_name',
            'category', 'category_name',
            'sender', 'assigned_to', 'created_at',
        ]


# Bilet detay serializer'ı — tüm alanlar + audit log
class TicketDetailSerializer(serializers.ModelSerializer):
    sender = UserShortSerializer(read_only=True)
    assigned_to = UserShortSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    history = TicketHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id', 'subject', 'message', 'attachment',
            'status', 'status_display', 'priority', 'priority_display',
            'resolution_note',
            'department', 'department_name', 'category', 'category_name',
            'sender', 'assigned_to',
            'created_at', 'updated_at', 'closed_at',
            'history',
        ]


# Bilet oluşturma serializer'ı
class TicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ['subject', 'message', 'department', 'category', 'priority', 'attachment']


# Bilet güncelleme serializer'ı
class TicketUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ['subject', 'message', 'department', 'category', 'priority', 'attachment']


# Bilet kapatma serializer'ı
class TicketCloseSerializer(serializers.Serializer):
    resolution_note = serializers.CharField(required=False, default='', allow_blank=True)


# Bilet transfer serializer'ı
class TicketTransferSerializer(serializers.Serializer):
    department = serializers.IntegerField()
    category = serializers.IntegerField(required=False, allow_null=True, default=None)
