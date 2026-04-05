"""
URL configuration for FestNest project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from events import views
from accounts import views as acc_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('search-suggestions/', views.search_suggestions, name='search_suggestions'),
    path('events/manage/', views.manage_events, name='manage_events'),
    path('events/create/', views.create_event, name='create_event'),
    path('events/<int:id>/edit/', views.edit_event, name='edit_event'),
    path('events/<int:id>/delete/', views.delete_event, name='delete_event'),
    path('category/<str:category>/', views.category_events, name='category'),
    path('event/<int:id>/', views.event_detail, name='event_detail'),
    path('my-registrations/', views.my_registrations, name='my_registrations'),
    path('event/<int:id>/team/create/', views.create_team, name='create_team'),
    path('event/<int:id>/team/join/', views.join_team, name='join_team'),
    path('event/<int:id>/team/leave/', views.leave_team, name='leave_team'),
    path('event/<int:id>/team/submit/', views.submit_team, name='submit_team'),
    path('signup/', acc_views.signup, name='signup'),
    path('login/', acc_views.user_login, name='login'),
    path('forgot-password/', acc_views.forgot_password_options, name='forgot_password_options'),
    path('forgot-password/mobile/', acc_views.forgot_password_mobile, name='forgot_password_mobile'),
    path(
        'forgot-password/mobile/verify/',
        acc_views.forgot_password_mobile_verify,
        name='forgot_password_mobile_verify',
    ),
    path(
        'forgot-password/email/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
        ),
        name='password_reset',
    ),
    path(
        'forgot-password/email/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'),
        name='password_reset_done',
    ),
    path(
        'forgot-password/email/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'),
        name='password_reset_confirm',
    ),
    path(
        'forgot-password/email/complete/',
        auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'),
        name='password_reset_complete',
    ),
    path('logout/', acc_views.user_logout, name='logout'),
    path('profile/', acc_views.profile_view, name='profile'),
    path('profile/edit/', acc_views.edit_profile, name='edit_profile'),
    path('profile/change-password/', acc_views.change_password, name='change_password'),
    path('profile/verify-email/', acc_views.request_email_verification, name='request_email_verification'),
    path('profile/verify-phone/', acc_views.request_phone_verification, name='request_phone_verification'),
    path('profile/verify-phone/confirm/', acc_views.verify_phone_otp, name='verify_phone_otp'),
    path(
        'profile/verify-email/<uidb64>/<token>/',
        acc_views.confirm_email_verification,
        name='confirm_email_verification',
    ),
    path('event/<int:id>/register/', views.register_event, name='register_event'),
    path('event/<int:id>/unregister/', views.unregister_event, name='unregister_event'),
    
]
