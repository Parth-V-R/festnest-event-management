from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.hashers import make_password, check_password
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import timedelta
import secrets
from .models import Profile
from .forms import ProfileForm

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect('home')
        messages.error(request, 'Invalid username or password.')

    return render(request, 'login.html')

def user_logout(request):
    logout(request)
    return redirect('home')

def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            messages.error(request, 'Username and password are required.')
            return redirect('signup')

        try:
            validate_password(password)
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
            return redirect('signup')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('signup')

        User.objects.create_user(username=username, password=password)
        messages.success(request, 'Account created successfully. Please log in.')
        return redirect('login')

    return render(request, 'signup.html')


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(
        request,
        'profile.html',
        {'profile': profile},
    )


@login_required
def edit_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile, user=request.user)
    return render(request, 'edit_profile.html', {'form': form})


@login_required
def request_email_verification(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if not request.user.email:
        messages.error(request, 'Add an Email ID first to verify it.')
        return redirect('edit_profile')
    if profile.email_verified:
        messages.info(request, 'Your Email ID is already verified.')
        return redirect('profile')

    uidb64 = urlsafe_base64_encode(force_bytes(request.user.pk))
    token = default_token_generator.make_token(request.user)
    verify_link = request.build_absolute_uri(
        reverse('confirm_email_verification', args=[uidb64, token]),
    )
    try:
        send_mail(
            subject='Verify your FestNest Email ID',
            message=f'Hi {request.user.username}, verify your email by opening this link: {verify_link}',
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@festnest.local'),
            recipient_list=[request.user.email],
            fail_silently=False,
        )
        messages.success(request, 'Verification mail sent. Please check your inbox.')
    except Exception:
        messages.error(request, 'Could not send verification email. Check email settings.')

    if settings.DEBUG:
        messages.info(request, f'DEBUG verify link: {verify_link}')
    return redirect('profile')


def confirm_email_verification(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        target_user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        target_user = None

    if target_user is None or not default_token_generator.check_token(target_user, token):
        messages.error(request, 'Verification link is invalid or expired.')
        if request.user.is_authenticated:
            return redirect('profile')
        return redirect('login')

    profile, _ = Profile.objects.get_or_create(user=target_user)
    profile.email_verified = True
    profile.save(update_fields=['email_verified'])
    messages.success(request, 'Email ID verified successfully.')
    if request.user.is_authenticated:
        return redirect('profile')
    return redirect('login')


@login_required
@require_POST
def request_phone_verification(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    phone = (profile.phone or '').strip()
    if not phone:
        messages.error(request, 'Add a mobile number first to verify it.')
        return redirect('edit_profile')
    if profile.phone_verified:
        messages.info(request, 'Your mobile number is already verified.')
        return redirect('profile')

    otp = f'{secrets.randbelow(1000000):06d}'
    profile.phone_otp_code = make_password(otp)
    profile.phone_otp_expires_at = timezone.now() + timedelta(minutes=10)
    profile.save(update_fields=['phone_otp_code', 'phone_otp_expires_at'])

    messages.success(request, 'OTP sent to your mobile number.')
    if settings.DEBUG:
        messages.info(request, f'DEBUG OTP: {otp}')
    return redirect('profile')


@login_required
@require_POST
def verify_phone_otp(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    submitted_otp = request.POST.get('otp', '').strip()
    if not submitted_otp:
        messages.error(request, 'Enter the OTP.')
        return redirect('profile')
    if not profile.phone_otp_code or not profile.phone_otp_expires_at:
        messages.error(request, 'Request OTP first.')
        return redirect('profile')
    if timezone.now() > profile.phone_otp_expires_at:
        profile.phone_otp_code = ''
        profile.phone_otp_expires_at = None
        profile.save(update_fields=['phone_otp_code', 'phone_otp_expires_at'])
        messages.error(request, 'OTP expired. Request a new OTP.')
        return redirect('profile')
    if not check_password(submitted_otp, profile.phone_otp_code):
        messages.error(request, 'Invalid OTP.')
        return redirect('profile')

    profile.phone_verified = True
    profile.phone_otp_code = ''
    profile.phone_otp_expires_at = None
    profile.save(update_fields=['phone_verified', 'phone_otp_code', 'phone_otp_expires_at'])
    messages.success(request, 'Mobile number verified successfully.')
    return redirect('profile')


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully.')
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {'form': form})


def forgot_password_options(request):
    return render(request, 'forgot_password_options.html')


def forgot_password_mobile(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        if not identifier:
            messages.error(request, 'Enter username or verified mobile number.')
            return redirect('forgot_password_mobile')

        user = User.objects.filter(username__iexact=identifier).first()
        profile = None
        if user:
            profile = Profile.objects.filter(user=user).first()
        if not user:
            profile = Profile.objects.filter(phone=identifier).select_related('user').first()
            user = profile.user if profile else None

        if not user or not profile:
            messages.error(request, 'Account not found.')
            return redirect('forgot_password_mobile')

        if not profile.phone or not profile.phone_verified:
            messages.error(request, 'This account does not have a verified mobile number.')
            return redirect('forgot_password_mobile')

        otp = f'{secrets.randbelow(1000000):06d}'
        profile.password_reset_otp_code = make_password(otp)
        profile.password_reset_otp_expires_at = timezone.now() + timedelta(minutes=10)
        profile.save(update_fields=['password_reset_otp_code', 'password_reset_otp_expires_at'])
        request.session['password_reset_mobile_user_id'] = user.id
        messages.success(request, 'OTP sent to your verified mobile number.')
        if settings.DEBUG:
            messages.info(request, f'DEBUG RESET OTP: {otp}')
        return redirect('forgot_password_mobile_verify')

    return render(request, 'forgot_password_mobile.html')


def forgot_password_mobile_verify(request):
    user_id = request.session.get('password_reset_mobile_user_id')
    if not user_id:
        messages.error(request, 'Start mobile reset first.')
        return redirect('forgot_password_mobile')

    user = User.objects.filter(pk=user_id).first()
    profile = Profile.objects.filter(user=user).first() if user else None
    if not user or not profile:
        messages.error(request, 'Reset session is invalid. Please try again.')
        request.session.pop('password_reset_mobile_user_id', None)
        return redirect('forgot_password_mobile')

    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        new_password1 = request.POST.get('new_password1', '')
        new_password2 = request.POST.get('new_password2', '')

        if not otp:
            messages.error(request, 'Enter OTP.')
            return redirect('forgot_password_mobile_verify')
        if not profile.password_reset_otp_code or not profile.password_reset_otp_expires_at:
            messages.error(request, 'Request OTP first.')
            return redirect('forgot_password_mobile')
        if timezone.now() > profile.password_reset_otp_expires_at:
            profile.password_reset_otp_code = ''
            profile.password_reset_otp_expires_at = None
            profile.save(update_fields=['password_reset_otp_code', 'password_reset_otp_expires_at'])
            messages.error(request, 'OTP expired. Request a new OTP.')
            return redirect('forgot_password_mobile')
        if not check_password(otp, profile.password_reset_otp_code):
            messages.error(request, 'Invalid OTP.')
            return redirect('forgot_password_mobile_verify')
        if new_password1 != new_password2:
            messages.error(request, 'New passwords do not match.')
            return redirect('forgot_password_mobile_verify')
        try:
            validate_password(new_password1, user=user)
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
            return redirect('forgot_password_mobile_verify')

        user.set_password(new_password1)
        user.save(update_fields=['password'])
        profile.password_reset_otp_code = ''
        profile.password_reset_otp_expires_at = None
        profile.save(update_fields=['password_reset_otp_code', 'password_reset_otp_expires_at'])
        request.session.pop('password_reset_mobile_user_id', None)
        messages.success(request, 'Password reset successful. Please login.')
        return redirect('login')

    return render(
        request,
        'forgot_password_mobile_verify.html',
        {'masked_phone': profile.phone},
    )

