# farmclassifieds/urls.py
from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('filter/', views.filtered_view, name='filtered_view'),
    path('posts/<int:pk>/', views.post_detail, name='post_detail'),
    path('posts/new/', views.post_create, name='post_create'),
    path('admin-verification/', views.admin_verification_list, name='admin_verification_list'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.PhoneLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
