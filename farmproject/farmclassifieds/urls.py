# farmclassifieds/urls.py
from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('filter/', views.filtered_view, name='filtered_view'),
    path('posts/<int:pk>/', views.post_detail, name='post_detail'),
    path('posts/new/', views.post_create, name='post_create'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.PhoneLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('my-posts/', views.my_posts, name='my_posts'),
path('posts/<int:pk>/edit/', views.post_edit, name='post_edit'),
path('posts/<int:pk>/delete/', views.post_delete, name='post_delete'),
path('admin-verification/', views.admin_verification, name='admin_verification'),

# path('moderation/posts/<int:pk>/approve/', views.admin_approve_post, name='admin_approve_post'),
# path('moderation/posts/<int:pk>/reject/', views.admin_reject_post, name='admin_reject_post'),

# path('admin/users/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),
path('posts/<int:pk>/renew/', views.renew_post, name='renew_post'),

# path('admin/users/<int:user_id>/limit/', views.admin_update_ad_limit, name='admin_update_ad_limit'),
# path('admin/posts/<int:pk>/extend/', views.admin_extend_post, name='admin_extend_post'),

# moderation URLs (NOT /admin/)
path('moderation/posts/<int:pk>/approve/', views.admin_approve_post, name='admin_approve_post'),
path('moderation/posts/<int:pk>/reject/', views.admin_reject_post, name='admin_reject_post'),
path('moderation/posts/<int:pk>/extend/', views.admin_extend_post, name='admin_extend_post'),

path('moderation/users/<int:user_id>/limit/', views.admin_update_ad_limit, name='admin_update_ad_limit'),
path('moderation/users/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),

path("browse/", views.select_district, name="select_district"),
path("browse/<str:district>/", views.select_category, name="select_category"),
path("browse/<str:district>/<str:category>/", views.posts_by_location, name="posts_by_location"),
path("search/", views.search_results, name="search_results"),

]
