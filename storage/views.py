from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import File, Folder, SharedLink, Activity
import json
import uuid
import os
from django.core.files.storage import default_storage
from .models import File, Folder


def dashboard(request):
    return render(request, "storage/dashboard.html")

def privacy(request):
    return render(request, "storage/privacy.html")

def terms(request):
    return render(request, "storage/terms.html")

def security(request):
    return render(request, "storage/security.html")


from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Support
from datetime import datetime

def support(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        desc = request.POST.get("desc")
        support = Support(name=name, email=email, desc=desc, date=datetime.today())
        support.save()


        # Add success message
        messages.success(request, "Your support request has been submitted successfully!")
        return redirect('support')
    

    return render(request, "storage/support.html")


@login_required
def index(request):
    """Main dashboard view"""
    folder_id = request.GET.get('folder')
    current_folder = None
    
    if folder_id:
        current_folder = get_object_or_404(Folder, id=folder_id, owner=request.user)
        files = File.objects.filter(folder=current_folder, owner=request.user)
        folders = Folder.objects.filter(parent=current_folder, owner=request.user)
    else:
        files = File.objects.filter(folder=None, owner=request.user)
        folders = Folder.objects.filter(parent=None, owner=request.user)
    
    # Combine files and folders for display
    items = []
    
    # Add folders
    for folder in folders:
        items.append({
            'id': folder.id,
            'name': folder.name,
            'type': 'folder',
            'size': '-',
            'modified': folder.updated_at.strftime('%b %d'),
            'icon': '📁'
        })
    
    # Add files
    for file in files:
        items.append({
            'id': file.id,
            'name': file.name,
            'type': 'file',
            'size': file.get_formatted_size(),
            'modified': file.updated_at.strftime('%b %d'),
            'icon': file.get_icon()
        })
    
    # Get recent activity
    activities = Activity.objects.filter(user=request.user)[:10]
    
    # Calculate storage usage using profile methods
    profile = request.user.profile
    storage_used_percent = profile.get_storage_used_percent()
    storage_used_gb = profile.get_storage_used_gb()
    storage_limit_gb = profile.get_storage_limit_gb()
    
    context = {
        'items': items,
        'current_folder': current_folder,
        'activities': activities,
        'storage_used_percent': round(storage_used_percent),
        'storage_used_gb': round(storage_used_gb, 1),
        'storage_limit_gb': storage_limit_gb,
    }
    
    return render(request, 'storage/index.html', context)


@login_required
@require_http_methods(["POST"])
def upload_file(request):
    """Handle file upload"""
    if 'files' not in request.FILES:
        return JsonResponse({'error': 'No files provided'}, status=400)
    
    folder_id = request.POST.get('folder_id')
    folder = None
    if folder_id:
        folder = get_object_or_404(Folder, id=folder_id, owner=request.user)
    
    uploaded_files = []
    
    for uploaded_file in request.FILES.getlist('files'):
        # Check storage limit using profile method
        profile = request.user.profile
        if not profile.can_upload_file(uploaded_file.size):
            return JsonResponse({
                'error': f'Storage limit exceeded! You have {profile.get_storage_used_gb():.1f} GB used of {profile.get_storage_limit_gb()} GB available.'
            }, status=400)
        
        # Check if file already exists
        if File.objects.filter(name=uploaded_file.name, folder=folder, owner=request.user).exists():
            # Generate unique name
            name, ext = os.path.splitext(uploaded_file.name)
            counter = 1
            while File.objects.filter(name=f"{name}_{counter}{ext}", folder=folder, owner=request.user).exists():
                counter += 1
            uploaded_file.name = f"{name}_{counter}{ext}"
        
        file_obj = File.objects.create(
            name=uploaded_file.name,
            file=uploaded_file,
            folder=folder,
            owner=request.user
        )
        
        # Update user's storage usage
        profile.storage_used += file_obj.size
        profile.save()
        
        # Log activity
        Activity.objects.create(
            user=request.user,
            action='upload',
            item_name=file_obj.name,
            details=f"Uploaded to {'root' if not folder else folder.name}"
        )
        
        uploaded_files.append({
            'id': file_obj.id,
            'name': file_obj.name,
            'size': file_obj.get_formatted_size(),
            'type': 'file',
            'icon': file_obj.get_icon()
        })
    
    return JsonResponse({'files': uploaded_files})

@login_required
@require_http_methods(["POST"])
def create_folder(request):
    """Create new folder"""
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'Folder name is required'}, status=400)
    
    parent_id = request.POST.get('parent_id')
    parent = None
    if parent_id:
        parent = get_object_or_404(Folder, id=parent_id, owner=request.user)
    
    # Check if folder already exists
    if Folder.objects.filter(name=name, parent=parent, owner=request.user).exists():
        return JsonResponse({'error': 'Folder already exists'}, status=400)
    
    folder = Folder.objects.create(
        name=name,
        parent=parent,
        owner=request.user
    )
    
    # Log activity
    Activity.objects.create(
        user=request.user,
        action='create_folder',
        item_name=folder.name,
        details=f"Created in {'root' if not parent else parent.name}"
    )
    
    return JsonResponse({
        'id': folder.id,
        'name': folder.name,
        'parent_id': parent.id if parent else None,
        'created_at': folder.created_at.strftime('%b %d')
    })


@login_required
def folder_contents(request, folder_id):
    """Get folder contents via AJAX"""
    folder = get_object_or_404(Folder, id=folder_id, owner=request.user)
    
    files = File.objects.filter(folder=folder, owner=request.user)
    subfolders = Folder.objects.filter(parent=folder, owner=request.user)
    
    items = []
    
    # Add subfolders
    for subfolder in subfolders:
        items.append({
            'id': subfolder.id,
            'name': subfolder.name,
            'type': 'folder',
            'size': '-',
            'modified': subfolder.updated_at.strftime('%b %d'),
            'icon': '📁'
        })
    
    # Add files
    for file in files:
        items.append({
            'id': file.id,
            'name': file.name,
            'type': 'file',
            'size': file.get_formatted_size(),
            'modified': file.updated_at.strftime('%b %d'),
            'icon': file.get_icon()
        })
    
    # <-- Add folder info here in the response
    return JsonResponse({
        'items': items,
        'folder_id': folder.id,
        'folder_name': folder.name,
        'parent_id': folder.parent.id if folder.parent else None
    })



@login_required
@require_http_methods(["POST"])
def delete_item(request, item_type, item_id):
    """Delete file or folder"""
    if item_type == 'file':
        item = get_object_or_404(File, id=item_id, owner=request.user)
        # Delete physical file
        if item.file and default_storage.exists(item.file.name):
            default_storage.delete(item.file.name)
    elif item_type == 'folder':
        item = get_object_or_404(Folder, id=item_id, owner=request.user)
        # Delete all files in folder recursively
        def delete_folder_contents(folder):
            for file in folder.files.all():
                if file.file and default_storage.exists(file.file.name):
                    default_storage.delete(file.file.name)
                file.delete()
            for subfolder in folder.subfolders.all():
                delete_folder_contents(subfolder)
                subfolder.delete()
        delete_folder_contents(item)
    else:
        return JsonResponse({'error': 'Invalid item type'}, status=400)
    
    # Log activity
    Activity.objects.create(
        user=request.user,
        action='delete',
        item_name=item.name
    )
    
    item.delete()
    return JsonResponse({'success': True})


@login_required
def download_file(request, file_id):
    """Download file"""
    file_obj = get_object_or_404(File, id=file_id, owner=request.user)
    
    if not file_obj.file or not default_storage.exists(file_obj.file.name):
        raise Http404("File not found")
    
    # Log activity
    Activity.objects.create(
        user=request.user,
        action='download',
        item_name=file_obj.name
    )
    
    response = HttpResponse(file_obj.file.read(), content_type=file_obj.mime_type)
    response['Content-Disposition'] = f'attachment; filename="{file_obj.name}"'
    return response


@login_required
def search(request):
    """Search files and folders"""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'items': []})
    
    files = File.objects.filter(
        Q(name__icontains=query) | Q(mime_type__icontains=query),
        owner=request.user
    )[:20]
    
    folders = Folder.objects.filter(
        name__icontains=query,
        owner=request.user
    )[:20]
    
    items = []
    
    for folder in folders:
        items.append({
            'id': folder.id,
            'name': folder.name,
            'type': 'folder',
            'size': '-',
            'modified': folder.updated_at.strftime('%b %d'),
            'icon': '📁',
            'path': folder.get_path()
        })
    
    for file in files:
        items.append({
            'id': file.id,
            'name': file.name,
            'type': 'file',
            'size': file.get_formatted_size(),
            'modified': file.updated_at.strftime('%b %d'),
            'icon': file.get_icon(),
            'path': file.folder.get_path() if file.folder else 'Root'
        })
    
    return JsonResponse({'items': items})


@login_required
def starred_files(request):
    """View starred files"""
    files = File.objects.filter(owner=request.user, is_starred=True)
    
    items = []
    for file in files:
        items.append({
            'id': file.id,
            'name': file.name,
            'type': 'file',
            'size': file.get_formatted_size(),
            'modified': file.updated_at.strftime('%b %d'),
            'icon': file.get_icon()
        })
    
    context = {
        'items': items,
        'page_title': 'Starred Files'
    }
    
    return render(request, 'storage/index.html', context)


@login_required
def recent_files(request):
    """View recent files"""
    files = File.objects.filter(owner=request.user).order_by('-updated_at')[:50]
    
    items = []
    for file in files:
        items.append({
            'id': file.id,
            'name': file.name,
            'type': 'file',
            'size': file.get_formatted_size(),
            'modified': file.updated_at.strftime('%b %d'),
            'icon': file.get_icon()
        })
    
    context = {
        'items': items,
        'page_title': 'Recent Files'
    }
    
    return render(request, 'storage/index.html', context)


@login_required
@require_http_methods(["POST"])
def rename_item(request, item_type, item_id):
    """Rename file or folder"""
    new_name = request.POST.get('name', '').strip()
    if not new_name:
        return JsonResponse({'error': 'Name is required'}, status=400)
    
    if item_type == 'file':
        item = get_object_or_404(File, id=item_id, owner=request.user)
        # Check if file with new name already exists
        if File.objects.filter(name=new_name, folder=item.folder, owner=request.user).exclude(id=item_id).exists():
            return JsonResponse({'error': 'File with this name already exists'}, status=400)
    elif item_type == 'folder':
        item = get_object_or_404(Folder, id=item_id, owner=request.user)
        # Check if folder with new name already exists
        if Folder.objects.filter(name=new_name, parent=item.parent, owner=request.user).exclude(id=item_id).exists():
            return JsonResponse({'error': 'Folder with this name already exists'}, status=400)
    else:
        return JsonResponse({'error': 'Invalid item type'}, status=400)
    
    old_name = item.name
    item.name = new_name
    item.save()
    
    # Log activity
    Activity.objects.create(
        user=request.user,
        action='rename',
        item_name=new_name,
        details=f"Renamed from '{old_name}'"
    )
    
    return JsonResponse({'success': True, 'new_name': new_name})


@login_required
@require_http_methods(["POST"])
def toggle_star(request, file_id):
    """Toggle star status of a file"""
    file_obj = get_object_or_404(File, id=file_id, owner=request.user)
    file_obj.is_starred = not file_obj.is_starred
    file_obj.save()
    
    return JsonResponse({'is_starred': file_obj.is_starred})

@login_required
def starred_files(request):
    files = File.objects.filter(owner=request.user, is_starred=True)

    items = []
    for file in files:
        items.append({
            'id': file.id,
            'name': file.name,
            'type': 'file',
            'size': file.get_formatted_size(),
            'modified': file.updated_at.strftime('%b %d'),
            'icon': file.get_icon()
        })

    # Calculate storage usage
    total_size = sum(f.size for f in File.objects.filter(owner=request.user))
    storage_limit = 100 * 1024 * 1024 * 1024  # 100GB
    storage_used_percent = min((total_size / storage_limit) * 100, 100)
    storage_used_gb = total_size / (1024 * 1024 * 1024)

    # Get recent activity
    activities = Activity.objects.filter(user=request.user)[:10]

    context = {
        'items': items,
        'page_title': 'Starred Files',
        'storage_used_percent': round(storage_used_percent),
        'storage_used_gb': round(storage_used_gb, 1),
        'storage_limit_gb': 100,
        'activities': activities,
    }

    return render(request, 'storage/index.html', context)


@login_required
def recent_files(request):
    files = File.objects.filter(owner=request.user).order_by('-updated_at')[:50]

    items = []
    for file in files:
        items.append({
            'id': file.id,
            'name': file.name,
            'type': 'file',
            'size': file.get_formatted_size(),
            'modified': file.updated_at.strftime('%b %d'),
            'icon': file.get_icon()
        })

    # Calculate storage usage
    total_size = sum(f.size for f in File.objects.filter(owner=request.user))
    storage_limit = 100 * 1024 * 1024 * 1024  # 100GB
    storage_used_percent = min((total_size / storage_limit) * 100, 100)
    storage_used_gb = total_size / (1024 * 1024 * 1024)

    # Get recent activity
    activities = Activity.objects.filter(user=request.user)[:10]

    context = {
        'items': items,
        'page_title': 'Recent Files',
        'storage_used_percent': round(storage_used_percent),
        'storage_used_gb': round(storage_used_gb, 1),
        'storage_limit_gb': 100,
        'activities': activities,
    }

    return render(request, 'storage/index.html', context)


from .models import SubscriptionPlan, UserSubscription
from django.contrib import messages

def subscription_plans(request):
    """Display subscription plans"""
    plans = SubscriptionPlan.objects.all()
    
    # Get current user's subscription
    current_subscription = None
    if request.user.is_authenticated:
        try:
            current_subscription = request.user.subscription
        except UserSubscription.DoesNotExist:
            pass
    
    context = {
        'plans': plans,
        'current_subscription': current_subscription,
    }
    return render(request, 'storage/subscriptions.html', context)

@login_required
def upgrade_subscription(request, plan_name):
    """Handle subscription upgrade"""
    try:
        plan = SubscriptionPlan.objects.get(name=plan_name)
        
        # Check if user already has this plan
        try:
            current_sub = request.user.subscription
            if current_sub.plan == plan and current_sub.is_active:
                messages.info(request, f"You already have the {plan.get_name_display()} plan.")
                return redirect('subscription_plans')
        except UserSubscription.DoesNotExist:
            pass
        
        # In a real application, you would integrate with Stripe here
        # For now, we'll just create/update the subscription
        
        UserSubscription.objects.update_or_create(
            user=request.user,
            defaults={
                'plan': plan,
                'is_active': True,
            }
        )
        
        # Update user's storage limit in profile
        profile = request.user.profile
        profile.save()  # This will trigger storage limit update
        
        messages.success(request, f"Successfully upgraded to {plan.get_name_display()} plan!")
        
    except SubscriptionPlan.DoesNotExist:
        messages.error(request, "Invalid subscription plan.")
    
    return redirect('subscription_plans')

@login_required
def downgrade_subscription(request):
    """Downgrade to free plan"""
    free_plan = SubscriptionPlan.objects.get(name='free')
    
    UserSubscription.objects.update_or_create(
        user=request.user,
        defaults={
            'plan': free_plan,
            'is_active': True,
        }
    )
    
    messages.success(request, "Downgraded to Free plan.")
    return redirect('subscription_plans')


from django.views.decorators.csrf import csrf_exempt
from .models import PaymentMethod, Transaction

@login_required
def payment_methods(request):
    """View and manage payment methods"""
    payment_methods = PaymentMethod.objects.filter(user=request.user)
    
    if request.method == 'POST':
        payment_type = request.POST.get('payment_type')
        provider = request.POST.get('provider')
        last_four = request.POST.get('last_four', '')
        
        # In a real app, you would integrate with payment processors like Stripe
        # This is a simplified version
        
        payment_method = PaymentMethod.objects.create(
            user=request.user,
            payment_type=payment_type,
            provider=provider,
            last_four=last_four
        )
        
        messages.success(request, f"Payment method added successfully!")
        return redirect('payment_methods')
    
    context = {
        'payment_methods': payment_methods,
        'payment_types': PaymentMethod.PAYMENT_TYPES,
    }
    return render(request, 'storage/payment_methods.html', context)

@login_required
def checkout(request, plan_name):
    """Checkout page for subscription plans"""
    try:
        plan = SubscriptionPlan.objects.get(name=plan_name)
        
        # Check if user already has this plan
        try:
            current_sub = request.user.subscription
            if current_sub.plan == plan and current_sub.is_active:
                messages.info(request, f"You already have the {plan.get_name_display()} plan.")
                return redirect('subscription_plans')
        except UserSubscription.DoesNotExist:
            pass
        
        payment_methods = PaymentMethod.objects.filter(user=request.user)
        
        if request.method == 'POST':
            # Process payment
            payment_method_id = request.POST.get('payment_method')
            try:
                payment_method = PaymentMethod.objects.get(id=payment_method_id, user=request.user)
                
                # Create transaction record
                transaction = Transaction.objects.create(
                    user=request.user,
                    amount=plan.price_monthly,
                    status='completed',  # In real app, this would depend on payment processor
                    payment_method=payment_method
                )
                
                # Update or create subscription
                UserSubscription.objects.update_or_create(
                    user=request.user,
                    defaults={
                        'plan': plan,
                        'is_active': True,
                    }
                )
                
                transaction.status = 'completed'
                transaction.completed_at = timezone.now()
                transaction.save()
                
                messages.success(request, f"Successfully upgraded to {plan.get_name_display()} plan!")
                return redirect('subscription_plans')
                
            except PaymentMethod.DoesNotExist:
                messages.error(request, "Invalid payment method.")
        
        context = {
            'plan': plan,
            'payment_methods': payment_methods,
        }
        return render(request, 'storage/checkout.html', context)
        
    except SubscriptionPlan.DoesNotExist:
        messages.error(request, "Invalid subscription plan.")
        return redirect('subscription_plans')

@login_required
def add_payment_method(request):
    """Add new payment method"""
    if request.method == 'POST':
        payment_type = request.POST.get('payment_type')
        provider = request.POST.get('provider')
        last_four = request.POST.get('last_four', '')
        
        # Basic validation
        if not payment_type or not provider:
            messages.error(request, "Please fill in all required fields.")
            return redirect('payment_methods')
        
        # In a real app, you would validate with payment processor
        payment_method = PaymentMethod.objects.create(
            user=request.user,
            payment_type=payment_type,
            provider=provider,
            last_four=last_four
        )
        
        messages.success(request, f"{provider} {payment_type.replace('_', ' ').title()} added successfully!")
        return redirect('payment_methods')
    
    context = {
        'payment_types': PaymentMethod.PAYMENT_TYPES,
    }
    return render(request, 'storage/add_payment_method.html', context)


@login_required
def set_default_payment_method(request, payment_method_id):
    """Set a payment method as default"""
    try:
        payment_method = PaymentMethod.objects.get(id=payment_method_id, user=request.user)
        
        # Remove default from all other payment methods
        PaymentMethod.objects.filter(user=request.user, is_default=True).update(is_default=False)
        
        # Set this one as default
        payment_method.is_default = True
        payment_method.save()
        
        messages.success(request, f"{payment_method.provider} set as default payment method.")
    except PaymentMethod.DoesNotExist:
        messages.error(request, "Payment method not found.")
    
    return redirect('payment_methods')