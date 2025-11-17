from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Profile
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login


def register(request):
    if request.user.is_authenticated:
        return redirect('index')
    else:
        if request.method == 'POST':
            username = request.POST['username']
            email = request.POST['email']
            password = request.POST['password']
            cpassword = request.POST['cpassword']
            firstname = request.POST['fname']
            lname = request.POST['lname']
            if username and password and email and cpassword and firstname and lname:
                if password == cpassword:
                    user = User.objects.create_user(username,email,password)
                    user.first_name = firstname
                    user.last_name = lname
                    user.save()
                    if user:
                        messages.success(request,"User Account Created")
                        return redirect("login")
                    else:
                        messages.error(request,"User Account Not Created")
                else:
                    messages.error(request,"Password Not Matched")
                    redirect("register")
        return render(request,'registration/register.html')
        

def login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)  # ✅ call Django’s login
            return redirect("index")    # change to your success page
        else:
            return render(request, "login.html", {"error": "Invalid username or password"})
    return render(request, "login.html")
        #return render(request, "home/login.html",)

from .models import Profile


from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.urls import reverse


def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # ✅ Use reverse() to generate the correct URL dynamically
            reset_link = request.build_absolute_uri(
                reverse('reset_password', kwargs={'uidb64': uid, 'token': token})
            )

            # ✅ Send email
            send_mail(
                'Password Reset - PiCloud',
                f'Hello {user.username},\n\nClick below to reset your password:\n{reset_link}\n\nIf you did not request this, ignore this email.',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            messages.success(request, "Password reset link sent to your email.")
        except User.DoesNotExist:
            messages.error(request, "No account found with this email.")
    return render(request, 'registration/forgot_password.html')


def reset_password(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None

    if user and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            password = request.POST.get('password')
            confirm = request.POST.get('confirm')
            if password == confirm:
                user.set_password(password)
                user.save()
                messages.success(request, "Password reset successfully.")
                return redirect('login')  # ✅ Redirect to login after reset
            else:
                messages.error(request, "Passwords do not match.")
        return render(request, 'registration/reset_password.html')
    else:
        messages.error(request, "Invalid or expired link.")
        return redirect('registration/forgot_password')  # ✅ Use name, not template path


from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Profile
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import update_session_auth_hash
from .forms import UserUpdateForm, ProfileUpdateForm, CustomPasswordChangeForm

# ... your existing register, login, forgot_password functions ...

from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Profile
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import update_session_auth_hash
from .forms import UserUpdateForm, ProfileUpdateForm, CustomPasswordChangeForm

# ... your existing register, login, forgot_password functions ...

@login_required
def profile(request):
    # Initialize forms outside the if-else blocks
    user_form = None
    profile_form = None
    password_form = None
    
    if request.method == 'POST':
        # Determine which form was submitted
        if 'user_update' in request.POST:
            user_form = UserUpdateForm(request.POST, instance=request.user)
            profile_form = ProfileUpdateForm(
                request.POST, 
                request.FILES, 
                instance=request.user.profile
            )
            
            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                profile_form.save()
                messages.success(request, '✅ Your profile has been updated successfully!')
                return redirect('profile')
            else:
                messages.error(request, '❌ Please correct the errors below.')
        
        elif 'password_change' in request.POST:
            password_form = CustomPasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, '✅ Your password has been changed successfully!')
                return redirect('profile')
            else:
                messages.error(request, '❌ Please correct the errors below.')
    
    # Initialize forms for GET request or if they weren't initialized in POST
    if user_form is None:
        user_form = UserUpdateForm(instance=request.user)
    if profile_form is None:
        profile_form = ProfileUpdateForm(instance=request.user.profile)
    if password_form is None:
        password_form = CustomPasswordChangeForm(request.user)
    
    # Calculate storage percentage for the progress bar
    storage_percentage = request.user.profile.get_storage_used_percent()
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'password_form': password_form,
        'storage_percentage': storage_percentage,
    }
    
    return render(request, "accounts/profile.html", context)

@login_required
def delete_profile_picture(request):
    if request.method == 'POST':
        # Set profile picture to default
        profile = request.user.profile
        if profile.image and profile.image.name != 'default.jpg':
            # Delete the old image file
            import os
            from django.conf import settings
            if hasattr(profile.image, 'path'):
                if os.path.isfile(profile.image.path):
                    os.remove(profile.image.path)
            profile.image = 'default.jpg'
            profile.save()
            messages.success(request, '✅ Profile picture removed successfully!')
        else:
            messages.info(request, 'ℹ️ You are already using the default profile picture.')
    
    return redirect('profile')