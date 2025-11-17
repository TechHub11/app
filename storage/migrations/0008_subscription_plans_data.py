from django.db import migrations

def create_subscription_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model('storage', 'SubscriptionPlan')
    
    plans = [
        {
            'name': 'free',
            'storage_gb': 15,
            'price_monthly': 0,
            'price_yearly': 0,
            'features': ['15 GB secure storage', 'Basic file sharing', 'Community support']
        },
        {
            'name': 'plus', 
            'storage_gb': 100,
            'price_monthly': 2.99,
            'price_yearly': 29.99,
            'features': ['100 GB secure storage', 'File version history', 'Expiring share links', 'Standard support']
        },
        {
            'name': 'pro',
            'storage_gb': 256,
            'price_monthly': 7.99,
            'price_yearly': 79.99,
            'features': ['256 GB secure storage', 'Priority sharing controls', 'Advanced security (2FA, encryption)', 'Priority support']
        },
        {
            'name': 'business',
            'storage_gb': 512,
            'price_monthly': 15.99,
            'price_yearly': 159.99,
            'features': ['512 GB shared storage (expandable)', 'Admin controls & audit logs', 'Secure team collaboration', '24/7 premium support']
        }
    ]
    
    for plan_data in plans:
        SubscriptionPlan.objects.create(**plan_data)

def reverse_func(apps, schema_editor):
    SubscriptionPlan = apps.get_model('storage', 'SubscriptionPlan')
    SubscriptionPlan.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('storage', '0007_support'),  # This depends on the last successful migration
    ]
    
    operations = [
        migrations.RunPython(create_subscription_plans, reverse_func),
    ]