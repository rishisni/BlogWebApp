
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from mainApp import views
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('privacypolicy/', views.privacy_policy, name='privacy'),
    path('aboutus/', views.about_us, name='aboutus'),
    path('terms-and-conditions/', views.terms_and_conditions, name='termsandconditions'),

    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('profile/<str:username>/', views.profile, name='profile'),    
    path('edit-profile/', views.edit_profile, name='edit-profile'),
    path('change-password/', views.change_password , name='change_password'),
    path('verify-email/<str:uidb64>/<str:token>/', views.verify_email, name='verify_email'),
    
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('social-auth/', include('social_django.urls', namespace='social')),
    
    path('social-auth/facebook/', include('social_django.urls', namespace='facebook')),
    path('social-auth/google-oauth2/', include('social_django.urls', namespace='google')),
    path('create-category/', views.create_category, name='create-category'),
    path('create-post/', views.create_post, name='create-post'),
    path('post-list/', views.post_list, name='post-list'),
    path('post-to-approve-list/', views.post_to_approve_list, name='post-to-approve-list'),
    path('approve-post/<int:post_id>/', views.approve_post, name='approve_post'),
    path('decline-post/<int:post_id>/', views.decline_post, name='decline_post'),
    path('categories/', views.category_list, name='category_list'),
    path('post/<int:post_id>/delete/', views.delete_post, name='delete-post'),
    path('post/<int:post_id>/edit/', views.edit_post, name='edit-post'),
    path('category/<int:category_id>/', views.category_posts, name='category-posts'),
    path('post/<int:post_id>/', views.full_post, name='full_post'),
    path('post/<int:post_id>/like/', views.like_post, name='like_post'),
    path('post/<int:post_id>/comment/', views.add_comment, name='add_comment'),
    path('follow/<str:username>/', views.follow_user, name='follow_user'),
    path('unfollow/<str:username>/', views.unfollow_user, name='unfollow_user'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    
    # User List and Promotion URLs
    path('users/', views.user_list, name='user_list'),
    path('promote/<int:user_id>/', views.promote_to_admin, name='promote_to_admin'),
    path('demote/<int:user_id>/', views.demote_to_user, name='demote_to_user'),
    
    path('add_competition/', views.add_competition, name='add_competition'),
    path('competition/<int:competition_id>/submit_entry/', views.submit_entry, name='submit_entry'),
    path('competition/<int:competition_id>/', views.competition_detail, name='competition_detail'),
    path('competitions/', views.competition_list, name='competition_list'),
    path('competition/<int:competition_id>/submitted_entries/', views.submitted_entries_list, name='submitted_entries_list'),
    path('user/submitted_entries/', views.user_submitted_entries_list, name='user_submitted_entries_list'),
    path('actions/', views.actions, name='actions'),
    path('add/', views.add_carousel_item, name='add_carousel_item'),
    path('edit/<int:id>/', views.edit_carousel_item, name='edit_carousel_item'),
    path('delete/<int:id>/', views.delete_carousel_item, name='delete_carousel_item'),
    path('set-password/', views.set_password, name='set_password'),
    path('view-profile/<str:username>/', views.view_user_profile, name='view_user_profile'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
