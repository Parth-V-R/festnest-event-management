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
from events import views
from accounts import views as acc_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('category/<str:category>/', views.category_events, name='category'),
    path('event/<int:id>/', views.event_detail, name='event_detail'),
    path('my-registrations/', views.my_registrations, name='my_registrations'),
    path('signup/', acc_views.signup, name='signup'),
    path('login/', acc_views.user_login, name='login'),
    path('logout/', acc_views.user_logout, name='logout'),
    path('event/<int:id>/register/', views.register_event, name='register_event'),
    path('event/<int:id>/unregister/', views.unregister_event, name='unregister_event'),
    
]
