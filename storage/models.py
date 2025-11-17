from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os
import magic




from django.core.files.storage import default_storage


class Folder(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subfolders')
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_starred = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['name', 'parent', 'owner']
    
    def __str__(self):
        return f"{self.name} ({'Root' if not self.parent else self.parent.name})"
    
    def get_path(self):
        """Get full path from root"""
        if self.parent:
            return f"{self.parent.get_path()}/{self.name}"
        return self.name
    
    def get_size(self):
        """Get total size of folder including all subfolders and files"""
        total_size = 0
        for file in self.files.all():
            total_size += file.size
        for subfolder in self.subfolders.all():
            total_size += subfolder.get_size()
        return total_size


def user_directory_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return f'user_{instance.owner.id}/{filename}'


class File(models.Model):
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to=user_directory_path)
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, null=True, blank=True, related_name='files')
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    size = models.BigIntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_shared = models.BooleanField(default=False)
    is_starred = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['name', 'folder', 'owner']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.file:
            self.size = self.file.size
            # Detect MIME type
            try:
                file_content = self.file.read()
                self.mime_type = magic.from_buffer(file_content, mime=True)
                self.file.seek(0)  # Reset file pointer
            except:
                self.mime_type = 'application/octet-stream'
        super().save(*args, **kwargs)
    
    def get_icon(self):
        """Return appropriate icon based on file type"""
        if self.mime_type.startswith('image/'):
            return '🖼️'
        elif self.mime_type.startswith('video/'):
            return '🎥'
        elif self.mime_type.startswith('audio/'):
            return '🎵'
        elif 'pdf' in self.mime_type:
            return '📕'
        elif any(word in self.mime_type for word in ['word', 'doc']):
            return '📄'
        elif any(word in self.mime_type for word in ['sheet', 'excel']):
            return '📊'
        elif any(word in self.mime_type for word in ['presentation', 'powerpoint']):
            return '📊'
        elif 'zip' in self.mime_type or 'compressed' in self.mime_type:
            return '📦'
        else:
            return '📄'
    
    def get_formatted_size(self):
        """Return human-readable file size"""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class SharedLink(models.Model):
    file = models.ForeignKey(File, on_delete=models.CASCADE, null=True, blank=True)
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, null=True, blank=True)
    token = models.CharField(max_length=64, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    access_count = models.IntegerField(default=0)
    
    def __str__(self):
        item = self.file or self.folder
        return f"Share link for {item.name}"
    
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class Activity(models.Model):
    ACTION_CHOICES = [
        ('upload', 'Uploaded'),
        ('download', 'Downloaded'),
        ('delete', 'Deleted'),
        ('rename', 'Renamed'),
        ('share', 'Shared'),
        ('move', 'Moved'),
        ('create_folder', 'Created folder'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    item_name = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username} {self.get_action_display()} {self.item_name}"
    


from django.db import models
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404


# Contact/Support messages
class Support(models.Model):
    name = models.CharField(max_length=122)
    email = models.CharField(max_length=122)
    desc = models.TextField()
    date = models.DateField()

    def __str__(self):
        return self.email
    

    # Add to storage/models.py
# Add these models to storage/models.py

class SubscriptionPlan(models.Model):
    PLAN_TYPES = [
        ('free', 'Free'),
        ('plus', 'Plus'),
        ('pro', 'Pro'),
        ('business', 'Business'),
    ]
    
    name = models.CharField(max_length=20, choices=PLAN_TYPES, unique=True)
    storage_gb = models.IntegerField()
    price_monthly = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    price_yearly = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    features = models.JSONField(default=list)
    
    def __str__(self):
        return f"{self.get_name_display()} - {self.storage_gb} GB"

class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"
    

    # Add to storage/models.py
class PaymentMethod(models.Model):
    PAYMENT_TYPES = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('paypal', 'PayPal'),
        ('google_pay', 'Google Pay'),
        ('phonepe', 'PhonePe'),
        ('upi', 'UPI'),
        ('net_banking', 'Net Banking'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    provider = models.CharField(max_length=100)  # Visa, MasterCard, etc.
    last_four = models.CharField(max_length=4, blank=True)  # Last 4 digits
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_payment_type_display()}"

class Transaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.amount} {self.currency}"