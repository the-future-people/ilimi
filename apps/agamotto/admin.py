from django.contrib import admin

from .models import DemoRequest


@admin.register(DemoRequest)
class DemoRequestAdmin(admin.ModelAdmin):
    list_display = ['name', 'school_name', 'phone', 'email', 'status', 'created_at']
    list_filter = ['status', 'source', 'created_at']
    search_fields = ['name', 'email', 'phone', 'school_name']
    list_editable = ['status']
    readonly_fields = ['ip_address', 'user_agent', 'created_at', 'updated_at']
    ordering = ['-created_at']