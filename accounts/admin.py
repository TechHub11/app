from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_storage_used_gb', 'get_storage_limit_gb', 'get_storage_used_percent']
    list_filter = ['user__is_active']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['get_storage_used_gb', 'get_storage_limit_gb', 'get_storage_used_percent']
    
    def get_storage_used_gb(self, obj):
        return f"{obj.get_storage_used_gb():.2f} GB"
    get_storage_used_gb.short_description = 'Storage Used'
    
    def get_storage_limit_gb(self, obj):
        return f"{obj.get_storage_limit_gb():.2f} GB"
    get_storage_limit_gb.short_description = 'Storage Limit'
    
    def get_storage_used_percent(self, obj):
        return f"{obj.get_storage_used_percent():.1f}%"
    get_storage_used_percent.short_description = 'Storage Used %'