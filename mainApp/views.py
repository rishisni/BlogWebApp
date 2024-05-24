from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm,SetPasswordForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives, send_mail
from django.shortcuts import redirect, render,get_object_or_404
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from .forms import *
from .models import *
from myproject import settings
from django.http import HttpResponseBadRequest,HttpResponseForbidden
from django.utils.html import strip_tags
import uuid
from django.db.models import Count ,Q
from datetime import datetime
import os
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone



# -----------------------------------------------------------Index/Home Page ----------------------------------------------------------------------

def index(request):
    
    all_posts = Post.objects.filter(approved=True).order_by('-created_at')    
   
    like_counts = [post.likes_count for post in all_posts]
    top_liked_posts = Post.objects.filter(approved=True).annotate(like_count=Count('likes')).order_by('-like_count')[:3]
    latest_posts = Post.objects.filter(approved=True).order_by('-created_at')[:3]
    categories = Category.objects.annotate(
        post_count=Count('post', filter=Q(post__approved=True))
    )
    submitted_entries = CompetitionEntry.objects.all()
    
    total_category_posts = Post.objects.filter(approved=True).count()
    carousel_items = CarouselItem.objects.filter(is_active=True)
    
    return render(request, 'index.html',
    {'all_posts': all_posts, 
    'categories': categories,
    'total_category_posts': total_category_posts, 
    'like_counts': like_counts,
    'submitted_entries': submitted_entries,
    'top_liked_posts':top_liked_posts,
    'latest_posts':latest_posts,
    'carousel_items': carousel_items,
    })



# -----------------------------------------------------------User RegisterPage ----------------------------------------------------------------------

def register(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            current_site = get_current_site(request)
            mail_subject = 'Activate your account'
            html_message = render_to_string('verification_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
                'verification_link': f"http://{current_site.domain}/verify-email/{urlsafe_base64_encode(force_bytes(user.pk))}/{default_token_generator.make_token(user)}/",
            })
            text_content = strip_tags(html_message)

            email = EmailMultiAlternatives(
                subject=mail_subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[form.cleaned_data.get('email')],
            )
            email.attach_alternative(html_message, "text/html")
            email.send()

            messages.success(request, 'Registration successful. Please check your email to verify your account.')
            return render(request, 'registration_success.html')
        else:
            # If form is invalid, display error messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")

            # Redirect back to the registration page with the form
            return render(request, 'register.html', {'form': form})
    else:
        form = SignUpForm()

    return render(request, 'register.html', {'form': form})



# -----------------------------------------------------------Verify Email ----------------------------------------------------------------------

# Verify Email View
def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Email verified successfully. You can now log in.')
        return redirect('login')
    else:
        messages.error(request, 'Invalid activation link. Please try registering again.')
        return HttpResponseBadRequest('Invalid activation link')


# -----------------------------------------------------------User Login Page ----------------------------------------------------------------------

def login(request):
    if request.user.is_authenticated:
        return redirect('profile', username=request.user.username)
    
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            username_or_phone_or_email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username_or_phone_or_email, password=password)
            if user is not None:
                auth_login(request, user)
                
                return redirect('profile', username=request.user.username)
            else:
                try:
                    user = User.objects.get(username=username_or_phone_or_email)
                    if user:
                        messages.error(request, 'Incorrect password.')
                except User.DoesNotExist:
                    messages.error(request, 'Invalid username, phone number, or email and password combination.')
        else:
            messages.error(request, 'Invalid username, phone number, or email and password combination.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'login.html', {'form': form})


# -----------------------------------------------------------User Profile ----------------------------------------------------------------------

@login_required
def profile(request, username):
    viewed_user = get_object_or_404(CustomUser, username=username)
    user_posts = Post.objects.filter(created_by=viewed_user)
    
    approved_posts = user_posts.filter(approved=True)
    pending_posts = user_posts.filter(approved=False, declined=False)
    declined_posts = user_posts.filter(declined=True)
    user_submitted_entries = CompetitionEntry.objects.filter(user=viewed_user)

    total_approved_posts = approved_posts.count()
    total_pending_posts = pending_posts.count()
    total_declined_posts = declined_posts.count()
    total_user_submitted_entries = user_submitted_entries.count()
    total_posts = total_approved_posts + total_user_submitted_entries

    profile = Profile.objects.filter(user=viewed_user).first()
    
    # Check if the viewed profile is the same as the logged-in user
    is_own_profile = request.user.username == username
    if is_own_profile:
        return render(request, 'profile.html', {
            'user': viewed_user,
            'profile': profile,
            'approved_posts': approved_posts,
            'pending_posts': pending_posts,
            'declined_posts': declined_posts,
            'total_posts': total_posts,
            'total_approved_posts': total_approved_posts,
            'total_pending_posts': total_pending_posts,
            'total_declined_posts': total_declined_posts,
            'user_submitted_entries': user_submitted_entries,
            'total_user_submitted_entries': total_user_submitted_entries,
        })
    else:
        is_following = request.user.is_authenticated and viewed_user.followers.filter(follower=request.user).exists()
        return render(request, 'view_user_profile.html', {
            'viewed_user': viewed_user,
            'profile': profile,
            'approved_posts': approved_posts,
            'total_posts': total_posts,
            'total_approved_posts': total_approved_posts,
            'user_submitted_entries': user_submitted_entries,
            'total_user_submitted_entries': total_user_submitted_entries,
            'profile_user': viewed_user,
            'is_following': is_following,
        })

# -----------------------------------------------------------Edit Profile ----------------------------------------------------------------------

@login_required
def edit_profile(request):
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile_image = request.FILES.get('profile_image')
            
            if profile_image:
                
                if profile.profile_image:
                    old_image_path = profile.profile_image.path
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)

                
                unique_filename = f"profile_image_{uuid.uuid4().hex}.jpg"
                profile.profile_image.save(unique_filename, profile_image)

            
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('profile', username=request.user.username)
        else:
            messages.error(request, 'There was an error updating your profile. Please check the form for errors.')
    else:
        form = ProfileForm(instance=profile)
    
    return render(request, 'edit_profile.html', {'form': form})



# -----------------------------------------------------------Chnage Passowrd ----------------------------------------------------------------------

@login_required
def change_password(request):
    if request.method == 'POST':
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            user = request.user
            current_password = form.cleaned_data['current_password']
            new_password = form.cleaned_data['new_password']
            confirm_new_password = form.cleaned_data['confirm_new_password']
            if user.check_password(current_password):
                if new_password == confirm_new_password:
                    user.set_password(new_password)
                    user.save()
                    update_session_auth_hash(request, user)  
                    messages.success(request, 'Your password was successfully changed.')
                    return redirect('profile', username=request.user.username)  
                else:
                    return render(request, 'change_password.html', {'form': form, 'error_message': 'New passwords do not match.'})
            else:
                return render(request, 'change_password.html', {'form': form, 'error_message': 'Incorrect current password.'})
    else:
        form = ChangePasswordForm()
    return render(request, 'change_password.html', {'form': form})



# -----------------------------------------------------------Set Password ----------------------------------------------------------------------

@login_required
def set_password(request):
    if request.method == 'POST':
        form = SetPasswordForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  
            messages.success(request, 'Your password was successfully set!')
            return redirect('profile', username=request.user.username)
        else:
            messages.error(request, 'Password Does Not Match.')
    else:
        form = SetPasswordForm(user=request.user)
    
    return render(request, 'set_password.html', {'form': form})



# -----------------------------------------------------------About Us ----------------------------------------------------------------------

def about_us(request):
    return render(request, 'about_us.html')



# -----------------------------------------------------------Privacy Policy ----------------------------------------------------------------------

def privacy_policy(request):
    return render(request, 'privacy.html')



# -----------------------------------------------------------Terms & Conditions ----------------------------------------------------------------------

def terms_and_conditions(request):
    return render(request, 'terms_and_conditions.html')



# -----------------------------------------------------------Create Category ----------------------------------------------------------------------

@login_required
def create_category(request):
    if request.user.is_admin or request.user.is_owner:
        if request.method == 'POST':
            form = CategoryForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Category created successfully.")
                return redirect('category_list')
            else:
                messages.error(request, "Category Already Exists")
        else:
            form = CategoryForm()
        return render(request, 'create_category.html', {'form': form})
    else:
        messages.error(request, "You are not authorized to access this page.")
        return redirect('index')



# -----------------------------------------------------------Category List----------------------------------------------------------------------

@login_required
def category_list(request):
    categories = Category.objects.annotate(
        post_count=Count('post', filter=Q(post__approved=True))
    )
    
    total_category_posts = Post.objects.filter(approved=True).count()
    
    return render(request, 'category_list.html', {'categories': categories, 'total_category_posts': total_category_posts})


# -----------------------------------------------------------Create Post ----------------------------------------------------------------------

@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.created_by = request.user
            if request.user.is_admin or request.user.is_owner:
                post.approved = True
            post.save()
            messages.success(request, 'Post created successfully.')
            return redirect('profile', username=request.user.username)  # Fix here
        else:
            messages.error(request, 'There was an error creating the post')
    else:
        form = PostForm()
    return render(request, 'create_post.html', {'form': form})



# ----------------------------------------------------------- Approved Post List  ----------------------------------------------------------------------

def post_list(request):
  
    posts = Post.objects.filter(approved=True).order_by('-created_at')

    return render(request, 'post_list.html', {'posts': posts})


# -----------------------------------------------------------Edit Post ----------------------------------------------------------------------

@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    if request.user != post.created_by:
        return HttpResponseForbidden("You are not authorized to edit this post.")
    
    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Post updated successfully.')
            return redirect('profile', username=post.created_by.username)  # Fix here
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PostForm(instance=post)
    return render(request, 'edit_post.html', {'form': form, 'post': post})


# -----------------------------------------------------------Delete Post ----------------------------------------------------------------------

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    if request.user == post.created_by or request.user.is_owner:
        if request.method == 'POST':
            post.delete()
            messages.success(request, 'Post has been deleted successfully.')
            return redirect('profile', username=request.user.username)  
        return render(request, 'delete_post.html', {'post': post})
    else:
        return HttpResponseForbidden("You are not authorized to access this page.")




# -----------------------------------------------------------Post To Approve List ( To be Approved by Admin/Owner) ----------------------------------------------------------------------

@login_required
def post_to_approve_list(request):
    if request.user.is_admin or request.user.is_owner:
        
        posts_to_approve = Post.objects.filter(approved=False).order_by('-created_at')
        return render(request, 'post_to_approve.html', {'posts_to_approve': posts_to_approve})
    else:
        messages.error(request, "You are not authorized to access this page.")
        return redirect('index')


# -----------------------------------------------------------Approve Post ----------------------------------------------------------------------

@login_required
def approve_post(request, post_id):
    if request.user.is_admin or request.user.is_owner:
        post = get_object_or_404(Post, id=post_id)
        post.approved = True
        post.save()
        messages.success(request, "Post approved successfully.")
        return redirect('post-to-approve-list')
    else:
        messages.error(request, "You are not authorized to perform this action.")
        return HttpResponseForbidden("You are not authorized to perform this action.")


# -----------------------------------------------------------Decline Post ----------------------------------------------------------------------

@login_required
def decline_post(request, post_id):
    if request.user.is_admin or request.user.is_owner:
        post = get_object_or_404(Post, id=post_id)
        post.declined = True
        post.save()
        messages.success(request, 'Post has been declined.')
        return redirect('post-to-approve-list')
    else:
        messages.error(request, "You are not authorized to perform this action.")
        return HttpResponseForbidden("You are not authorized to perform this action.")



# ----------------------------------------------------------- Category Post ----------------------------------------------------------------------

def category_posts(request, category_id):
    category = Category.objects.get(pk=category_id)
    posts = Post.objects.filter(category=category, approved=True).order_by('-created_at')
    
    
    like_counts = [post.likes_count for post in posts]
    
    post_count = posts.count()  
    return render(request, 'category_posts.html', {'category': category, 'posts': posts, 'post_count': post_count, 'like_counts': like_counts})




# -----------------------------------------------------------View Full Detail of Post ----------------------------------------------------------------------

from django.db.models import F


def full_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    # Check if the user is authenticated and is the creator of the post or is an owner
    can_view_unapproved_post = False
    if request.user.is_authenticated:
        if request.user == post.created_by or getattr(request.user, 'is_owner', False):
            can_view_unapproved_post = True

    # If the post is not approved and the user is not the creator or owner, redirect or handle differently
    if not post.approved and not can_view_unapproved_post:
        # Handle the case where the post is not approved and the user is not authorized to view it
        messages.error(request, "You are not authorized to access this page.")
        return redirect('index')

    # Fetch comments ordered by their creation date in descending order (latest first)
    comments = post.comments.order_by('-created_at')

    liked = False
    like_count = post.likes.count()

    if request.method == 'POST':
        if 'like' in request.POST:
            if request.user.is_authenticated and request.user not in post.likes.all():
                post.likes.add(request.user)
        elif 'unlike' in request.POST:
            if request.user.is_authenticated and request.user in post.likes.all():
                post.likes.remove(request.user)
        elif 'comment' in request.POST:
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.post = post
                comment.user = request.user
                comment.save()
                messages.success(request, "Your comment has been added successfully!")
            else:
                messages.error(request, "Invalid comment. Please try again.")
    else:
        comment_form = CommentForm()

    liked = request.user.is_authenticated and request.user in post.likes.all()

    return render(request, 'full_post.html', {'post': post, 'comments': comments, 'like_count': like_count, 'liked': liked, 'comment_form': comment_form})



# -----------------------------------------------------------Add Comment to Post ----------------------------------------------------------------------

@login_required
def add_comment(request, post_id):
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            post = get_object_or_404(Post, id=post_id)
            comment = form.save(commit=False)
            comment.post = post
            comment.user = request.user
            comment.save()
            messages.success(request, "Your comment has been added successfully!")
        else:
            messages.error(request, "Invalid comment. Please try again.")
    return redirect('full_post', post_id=post_id)


# -----------------------------------------------------------Delete Comment's Post ----------------------------------------------------------------------


@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    # Only allow owners to delete comments
    if getattr(request.user, 'is_owner', False):
        comment.delete()
        messages.success(request, "Comment deleted successfully.")
    else:
        messages.error(request, "You are not authorized to delete this comment.")

    return redirect('full_post', post_id=comment.post.id)



# -----------------------------------------------------------Like/Unlike Post ----------------------------------------------------------------------

@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    if post.likes.filter(id=request.user.id).exists():
        post.likes.remove(request.user)
        post.update_likes_count()  
        messages.success(request, 'You have unliked the post.')
    else:
        post.likes.add(request.user)
        post.update_likes_count()  
        messages.success(request, 'You have liked the post.')
    
    return redirect('full_post', post_id=post_id)



# -----------------------------------------------------------Follow User ----------------------------------------------------------------------

@login_required
def follow_user(request, username):
    if request.method == 'POST':
        followee = CustomUser.objects.get(username=username)
        follow, created = Follow.objects.get_or_create(follower=request.user, followee=followee)
        if not created:
            messages.info(request, f"You are already following {followee.username}.")
        else:
            messages.success(request, f"You are now following {followee.username}.")
    return redirect('profile', username=username)


# ----------------------------------------------------------- Unfollow User ----------------------------------------------------------------------

@login_required
def unfollow_user(request, username):
    if request.method == 'POST':
        followee = CustomUser.objects.get(username=username)
        try:
            follow = Follow.objects.get(follower=request.user, followee=followee)
            follow.delete()
            messages.success(request, f"You have unfollowed {followee.username}.")
        except Follow.DoesNotExist:
            messages.error(request, f"You are not following {followee.username}.")
    return redirect('profile', username=username)

# -----------------------------------------------------------All User List  ----------------------------------------------------------------------

@login_required
def user_list(request):
    if request.user.is_owner:
        users = CustomUser.objects.all()
        
        return render(request, 'user_list.html', {'users': users})
    else:
        messages.error(request, "You are not authorized to access this page.")
        return redirect('index')



# -----------------------------------------------------------Promot User to Admin ----------------------------------------------------------------------

@login_required
def promote_to_admin(request, user_id):
    if request.user.is_owner:  # Only the owner can promote users
        user = get_object_or_404(CustomUser, id=user_id)
        user.is_admin = True
        user.save()
        messages.success(request, f"{user.username} has been promoted to admin.")
    else:
        messages.error(request, "You are not authorized to perform this action.")
    return redirect('user_list')



# -----------------------------------------------------------Demote Admin to User ----------------------------------------------------------------------

@login_required
def demote_to_user(request, user_id):
    if request.user.is_owner:  # Only the owner can demote users
        user = get_object_or_404(CustomUser, id=user_id)
        user.is_admin = False
        user.save()
        messages.success(request, f"{user.username} has been demoted to user.")
    else:
        messages.error(request, "You are not authorized to perform this action.")
    return redirect('user_list')



# -----------------------------------------------------------Add Competition ----------------------------------------------------------------------

@login_required
def add_competition(request):
    if request.method == 'POST':
        form = CompetitionForm(request.POST, request.FILES)
        if form.is_valid():
            competition = form.save(commit=False)
            competition.owner = request.user
            competition.save()
            
            messages.success(request, "Competition added successfully.")
            return redirect('competition_list')
        else:
            
            messages.error(request, "Failed to add competition. Please check the form and try again.")
    else:
        if request.user.is_authenticated and (request.user.is_admin or request.user.is_owner):
            form = CompetitionForm()
            return render(request, 'add_competition.html', {'form': form})
        else:
            return redirect('index')



# -----------------------------------------------------------Competition List ----------------------------------------------------------------------

def competition_list(request):
    competitions = Competition.objects.all()

    if competitions.exists():
        current_date = timezone.now()

        new_competitions = sorted([comp for comp in competitions if comp.end_date > current_date], key=lambda x: x.end_date, reverse=True)
        old_competitions = sorted([comp for comp in competitions if comp.end_date <= current_date], key=lambda x: x.end_date)

        return render(request, 'competition_list.html', {'new_competitions': new_competitions, 'old_competitions': old_competitions})
    else:
        
        return render(request, 'competition_list.html')



# -----------------------------------------------------------Competition Details ----------------------------------------------------------------------

def competition_detail(request, competition_id):
    try:
        competition = Competition.objects.get(pk=competition_id)
        categories = Category.objects.all()
        return render(request, 'competition_detail.html', {'competition': competition, 'categories': categories})
    except Competition.DoesNotExist:
        messages.error(request, 'Competition does not exist.')
        return redirect('competition_list')



# -----------------------------------------------------------User Participation Form ----------------------------------------------------------------------

@login_required
def submit_entry(request, competition_id):
    competition = get_object_or_404(Competition, pk=competition_id)

    if competition.end_date <= timezone.now():
        messages.error(request, "क्षमा करें, प्रविष्टियां पहले ही समाप्त हो चुकी है। आप कोई पोस्ट सबमिट नहीं कर सकते.")
        return redirect('competition_detail', competition_id=competition_id)

    entry = CompetitionEntry.objects.filter(competition=competition, user=request.user).first()
    if entry:
        messages.error(request, "क्षमा करें, आप केवल एक पोस्ट सबमिट कर सकते हैं।")
        return redirect('competition_detail', competition_id=competition_id)

    if request.method == 'POST':
        form = CompetitionEntryForm(request.POST, request.FILES)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.competition = competition
            entry.user = request.user
            entry.save()
            messages.success(request, "Your entry has been submitted successfully.")
            return redirect('user_submitted_entries_list')
    else:
        form = CompetitionEntryForm()

    return render(request, 'submit_entry.html', {'form': form, 'competition': competition})



# ----------------------------------------------------------- All User Particpation Post List ----------------------------------------------------------------------

@login_required
def submitted_entries_list(request, competition_id):
    competition = get_object_or_404(Competition, pk=competition_id)
    entries = CompetitionEntry.objects.filter(competition=competition)
    return render(request, 'entries_list.html', {'competition': competition, 'entries': entries})


# ----------------------------------------------------------- User Particpation Post List ----------------------------------------------------------------------

@login_required
def user_submitted_entries_list(request):
    user = request.user
    entries = CompetitionEntry.objects.filter(user=user)
    return render(request, 'profile.html', {'user': user, 'entries': entries})



# ----------------------------------------------------------- Owner/Admin Actions ----------------------------------------------------------------------

@login_required
def actions(request):
    if request.user.is_owner or request.user.is_admin:
        return render(request, 'actions.html')
    else:
        messages.error(request, "You are not authorized to access this page.")
        return redirect('index')




# ----------------------------------------------------------- Add Carousel Items  ----------------------------------------------------------------------

@login_required
def add_carousel_item(request):
    if request.user.is_admin or request.user.is_owner:
        if request.method == 'POST':
            form = CarouselItemForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, "Carousel item added successfully.")
                return redirect('index')
            else:
                messages.error(request, "Failed to add carousel item. Please check the form and try again.")
        else:
            form = CarouselItemForm()
        return render(request, 'add_carousel_item.html', {'form': form})
    else:
        messages.error(request, "You are not authorized to access this page.")
        return redirect('index')



# ----------------------------------------------------------- Edit Carousel Items  ----------------------------------------------------------------------

@login_required
def edit_carousel_item(request, id):
    item = get_object_or_404(CarouselItem, id=id)
    
    if request.user.is_admin or request.user.is_owner:
        if request.method == 'POST':
            form = CarouselItemForm(request.POST, request.FILES, instance=item)
            if form.is_valid():
                form.save()
                messages.success(request, "Carousel item updated successfully.")
                return redirect('index')
            else:
                messages.error(request, "Failed to update carousel item. Please check the form and try again.")
        else:
            form = CarouselItemForm(instance=item)
        return render(request, 'edit_carousel_item.html', {'form': form})
    else:
        messages.error(request, "You are not authorized to access this page.")
        return redirect('index')


# ----------------------------------------------------------- Delete Carousel Items  ----------------------------------------------------------------------

@login_required
def delete_carousel_item(request, id):
    item = get_object_or_404(CarouselItem, id=id)
    if request.user.is_admin or request.user.is_owner:
        if item.image:
            image_path = os.path.join(settings.MEDIA_ROOT, item.image.path)
            if os.path.isfile(image_path):
                os.remove(image_path)
        
        item.delete()
        messages.success(request, "Carousel item and its image deleted successfully.")
        return redirect('index')
    else:
        messages.error(request, "You are not authorized to access this page.")
        return redirect('index')



# ----------------------------------------------------------- Delete User( Only Owner Can Perform)  ----------------------------------------------------------------------

@login_required
def delete_user(request, user_id):
    if request.user.is_owner:
        user_to_delete = get_object_or_404(CustomUser, id=user_id)
        if user_to_delete != request.user:
            user_to_delete.delete()
            messages.success(request, "User deleted successfully.")
        else:
            messages.error(request, "You cannot delete your own account.")
    else:
        messages.error(request, "You are not authorized to delete users.")
    return redirect('user_list')




def post_search(request):
    query = request.GET.get('q')
    posts = Post.objects.filter(approved=True).order_by('-created_at')

    if query:
        posts = posts.filter(
            models.Q(created_by__username__icontains=query) |  # Search by username
            models.Q(title__icontains=query) |  # Search by post title
            models.Q(description__icontains=query)  # Search by description
            # Add more fields to search if needed
        )

    context = {
        'posts': posts,
        'search_query': query  # Renamed to match the template variable
    }
    return render(request, 'search_results.html', context)
