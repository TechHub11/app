from django.contrib import admin
from .models import File, Folder, SharedLink, Activity


from .models import Support

# Register your models here.
admin.site.register(Support)

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'folder', 'size', 'mime_type', 'created_at']
    list_filter = ['mime_type', 'created_at', 'is_starred']
    search_fields = ['name', 'owner__username']
    readonly_fields = ['size', 'mime_type', 'created_at', 'updated_at']


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'parent', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'owner__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SharedLink)
class SharedLinkAdmin(admin.ModelAdmin):
    list_display = ['token', 'file', 'folder', 'created_by', 'created_at', 'access_count']
    list_filter = ['created_at']
    readonly_fields = ['token', 'created_at']


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'item_name', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['user__username', 'item_name']
    readonly_fields = ['timestamp']

    from django.contrib import admin
from .models import File, Folder, SharedLink, Activity, Support, SubscriptionPlan, UserSubscription

# ... your existing admin registrations ...

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'storage_gb', 'price_monthly', 'price_yearly']
    list_filter = ['name']
    search_fields = ['name']

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'is_active', 'start_date', 'end_date']
    list_filter = ['plan', 'is_active', 'start_date']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['start_date']