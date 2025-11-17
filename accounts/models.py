from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
        ('Prefer not to say', 'Prefer not to say'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(default='default.jpg', upload_to='profile_pics')
    storage_used = models.BigIntegerField(default=0)  # bytes
    
    # Add these new fields
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def get_storage_used_gb(self):
        return self.storage_used / (1024 * 1024 * 1024)
    
    def get_storage_limit_gb(self):
        """Get storage limit from subscription plan"""
        try:
            if hasattr(self.user, 'subscription') and self.user.subscription.is_active:
                return self.user.subscription.plan.storage_gb
            else:
                # Default free plan
                return 15
        except:
            return 15
    
    def get_storage_limit_bytes(self):
        """Get storage limit in bytes"""
        return self.get_storage_limit_gb() * 1024 * 1024 * 1024
    
    def get_storage_used_percent(self):
        storage_limit = self.get_storage_limit_bytes()
        if storage_limit == 0:
            return 0
        return min((self.storage_used / storage_limit) * 100, 100)
    
    def can_upload_file(self, file_size):
        """Check if user can upload file based on their storage limit"""
        return (self.storage_used + file_size) <= self.get_storage_limit_bytes()

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        Profile.objects.create(user=instance)