from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
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
from django.db.models import Count 
from datetime import datetime


def index(request):
    # Get all posts
    all_posts = Post.objects.filter(approved=True).order_by('-created_at')    
    # Fetch the like count for each post
    like_counts = [post.likes_count for post in all_posts]
    top_liked_posts = Post.objects.filter(approved=True).annotate(like_count=Count('likes')).order_by('-like_count')[:3]
    latest_posts = Post.objects.filter(approved=True).order_by('-created_at')[:3]
    # Get categories and annotate each category with the count of posts in it
    categories = Category.objects.annotate(post_count=Count('post'))
    submitted_entries = CompetitionEntry.objects.all()
    # Calculate the total count of all category posts
    total_category_posts = Post.objects.count()
    
    return render(request, 'index.html', {'all_posts': all_posts,  'categories': categories, 'total_category_posts': total_category_posts, 'like_counts': like_counts,'submitted_entries': submitted_entries,'top_liked_posts':top_liked_posts,'latest_posts':latest_posts})


def category_posts(request, category_id):
    category = Category.objects.get(pk=category_id)
    posts = Post.objects.filter(category=category, approved=True)
    
    # Fetch the like count for each post
    like_counts = [post.likes_count for post in posts]
    
    post_count = posts.count()  # Count the number of posts in this category
    return render(request, 'category_posts.html', {'category': category, 'posts': posts, 'post_count': post_count, 'like_counts': like_counts})

def register(request):
    if request.user.is_authenticated:
        return redirect('profile')
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
                body=text_content,  # Plain text content
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[form.cleaned_data.get('email')],
            )
            email.attach_alternative(html_message, "text/html")

            email.send()

            return render(request, 'registration_success.html')
    else:
        form = SignUpForm()
    
    return render(request, 'register.html', {'form': form})

def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Email verified successfully. You can now log in.')
        return redirect('login')
    else:
        return HttpResponseBadRequest('Invalid activation link')
        
def login(request):
    if request.user.is_authenticated:
        return redirect('profile')
    
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                auth_login(request, user)
                messages.success(request, 'Login successful.')
                return redirect('profile')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'login.html', {'form': form})

@login_required
def profile(request):
    user = request.user
    user_posts = Post.objects.filter(created_by=user)
    # Get all approved posts created by the user
    approved_posts = user_posts.filter(approved=True)
    # Get all pending posts created by the user
    pending_posts = user_posts.filter(approved=False, declined=False)
    # Get all declined posts created by the user
    declined_posts = user_posts.filter(declined=True)
    user_submitted_entries = CompetitionEntry.objects.filter(user=request.user)
    # Count the number of each type of post
    
    total_approved_posts = approved_posts.count()
    total_pending_posts = pending_posts.count()
    total_declined_posts = declined_posts.count()
    total_user_submitted_entries = user_submitted_entries.count()
    total_posts = total_approved_posts + total_user_submitted_entries
    profile = Profile.objects.filter(user=user).first()
    
    return render(request, 'profile.html', {
        'user': user,
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


@login_required
def edit_profile(request):
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            # Generate a unique filename for the profile image
            profile_image = request.FILES.get('profile_image')
            if profile_image:
                unique_filename = f"profile_image_{uuid.uuid4().hex}.jpg"
                profile.profile_image.save(unique_filename, profile_image)
            form.save()
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'edit_profile.html', {'form': form})

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
                    update_session_auth_hash(request, user)  # Update session with new password hash
                    return redirect('password_change_done')
                else:
                    return render(request, 'change_password.html', {'form': form, 'error_message': 'New passwords do not match.'})
            else:
                return render(request, 'change_password.html', {'form': form, 'error_message': 'Incorrect current password.'})
    else:
        form = ChangePasswordForm()
    return render(request, 'change_password.html', {'form': form})


def about_us(request):
    return render(request, 'about_us.html')

def privacy_policy(request):
    return render(request, 'privacy.html')

def terms_and_conditions(request):
    return render(request, 'terms_and_conditions.html')

@login_required
def create_category(request):
    if request.user.is_admin or request.user.is_owner:
        if request.method == 'POST':
            form = CategoryForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('category_list')
        else:
            form = CategoryForm()
        return render(request, 'create_category.html', {'form': form})
    else:
        messages.error(request, "You are not authorized to access this page.")
        return redirect('index')

@login_required
def approve_post(request, post_id):
    if request.user.is_admin or request.user.is_owner:
        post = Post.objects.get(id=post_id)
        post.approved = True
        post.save()
        return redirect('post-to-approve-list')
    else:
        return HttpResponseForbidden("You are not authorized to perform this action.")


@login_required
def decline_post(request, post_id):
    if request.user.is_admin or request.user.is_owner:
        post = get_object_or_404(Post, id=post_id)
        post.declined = True  # Assuming you have an 'approved' field in your Post model
        post.save()
        messages.success(request, 'Post has been declined.')
        return redirect('post-to-approve-list')
    else:
        return HttpResponseForbidden("You are not authorized to perform this action.")

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
            return redirect('profile')
    else:
        form = PostForm()
    return render(request, 'create_post.html', {'form': form})



def post_list(request):
    # Get all approved posts
    posts = Post.objects.filter(approved=True).order_by('-created_at')

    return render(request, 'post_list.html', {'posts': posts})


@login_required
def category_list(request):
    # Annotate each category with the count of related posts
    categories = Category.objects.annotate(post_count=Count('post'))
    
    # Calculate the total count of all category posts
    total_category_posts = Post.objects.count()
    
    return render(request, 'category_list.html', {'categories': categories, 'total_category_posts': total_category_posts})
@login_required
def post_to_approve_list(request):
    if request.user.is_admin or request.user.is_owner:
        # Get posts that are not approved yet
        posts_to_approve = Post.objects.filter(approved=False).order_by('-created_at')
        return render(request, 'post_to_approve.html', {'posts_to_approve': posts_to_approve})
    else:
        messages.error(request, "You are not authorized to access this page.")
        return redirect('index')



@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    # Check if the logged-in user is the creator of the post
    if request.user != post.created_by:
        return HttpResponseForbidden("You are not authorized to edit this post.")
    
    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = PostForm(instance=post)
    return render(request, 'edit_post.html', {'form': form, 'post': post})

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    # Check if the logged-in user is the creator of the post or is an owner
    if request.user == post.created_by or request.user.is_owner:
        if request.method == 'POST':
            post.delete()
            messages.success(request, 'Post has been deleted successfully.')
            return redirect('profile')  # Adjust this to redirect to the appropriate URL
        return render(request, 'delete_post.html', {'post': post})
    else:
        messages.error(request, "You are not authorized to access this page.")
        return redirect('index')

def full_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.all()  # Get all comments related to this post

    # Check if the user has already liked this post
    liked = False
    like_count = post.likes_count  # Fetch the like count directly from the post model

    if request.user.is_authenticated:
        liked = post.likes.filter(id=request.user.id).exists()

    # Handle like/unlike action
    if request.method == 'POST':
        if request.user.is_authenticated:
            if 'like' in request.POST:
                if not liked:
                    post.likes.add(request.user)
                    post.update_likes_count()  # Update the like count
            elif 'unlike' in request.POST:
                if liked:
                    post.likes.remove(request.user)
                    post.update_likes_count()  # Update the like count
            return redirect('full_post', post_id=post_id)
        else:
            return redirect('login')

    # Comment functionality
    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.user = request.user
            comment.save()
            return redirect('full_post', post_id=post_id)
    else:
        comment_form = CommentForm()

    return render(request, 'full_post.html', {'post': post, 'comments': comments, 'like_count': like_count, 'liked': liked, 'comment_form': comment_form})

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
    return redirect('full_post', post_id=post_id)

@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    # Check if the user has already liked the post
    if post.likes.filter(id=request.user.id).exists():
        # If the user has already liked the post, remove the like
        post.likes.remove(request.user)
        post.update_likes_count()  # Update the like count
    else:
        # If the user hasn't liked the post yet, add the like
        post.likes.add(request.user)
        post.update_likes_count()  # Update the like count
    
    return redirect('full_post', post_id=post_id)




@login_required
def follow_user(request, user_id):
    followee = get_object_or_404(CustomUser, id=user_id)
    if request.user != followee:  # Users can't follow themselves
        Follow.objects.get_or_create(follower=request.user, followee=followee)
        messages.success(request, "Followed successfully.")
    return redirect(request.POST.get('next', request.META.get('HTTP_REFERER', 'profile')))

@login_required
def unfollow_user(request, user_id):
    followee = get_object_or_404(CustomUser, id=user_id)
    if request.user != followee:  # Users can't unfollow themselves
        Follow.objects.filter(follower=request.user, followee=followee).delete()
        messages.success(request, "Unfollowed successfully.")
    return redirect(request.POST.get('next', request.META.get('HTTP_REFERER', 'profile')))

@login_required
def user_list(request):
    if request.user.is_owner:
        users = CustomUser.objects.all()
        return render(request, 'user_list.html',{'users':users})
    else:
        messages.error(request, "You are not authorized to access this page.")
        return redirect('index')
    

# views.py
@login_required
def promote_to_admin(request, user_id):
    if request.user.is_owner:  # Only the owner can promote users
        user = get_object_or_404(CustomUser, id=user_id)
        user.is_admin = True
        user.save()
    return redirect('user_list')

@login_required
def demote_to_user(request, user_id):
    if request.user.is_owner:  # Only the owner can demote users
        user = get_object_or_404(CustomUser, id=user_id)
        user.is_admin = False
        user.save()
    return redirect('user_list')

from django.utils import timezone

def competition_list(request):
    competitions = Competition.objects.all()

    # Convert current date to timezone-aware datetime
    current_date = timezone.now()

    # Split competitions into new and old based on start date
    new_competitions = sorted([comp for comp in competitions if comp.end_date > current_date], key=lambda x: x.end_date, reverse=True)
    old_competitions = sorted([comp for comp in competitions if comp.end_date <= current_date], key=lambda x: x.end_date)

    return render(request, 'competition_list.html', {'new_competitions': new_competitions, 'old_competitions': old_competitions})

def competition_detail(request, competition_id):
    competition = Competition.objects.get(pk=competition_id)
    categories = Category.objects.all()
    return render(request, 'competition_detail.html', {'competition': competition, 'categories': categories})


from django.utils import timezone
from django.contrib import messages

@login_required
def submit_entry(request, competition_id):
    competition = get_object_or_404(Competition, pk=competition_id)

    # Check if the competition has already ended
    if competition.end_date <= timezone.now():
        # Display an error message
        messages.error(request, "क्षमा करें, प्रतियोगिता पहले ही समाप्त हो चुकी है। आप कोई प्रविष्टि सबमिट नहीं कर सकते.")
        # Redirect the user to the competition detail page or any other page
        return redirect('competition_detail', competition_id=competition_id)

    entry = CompetitionEntry.objects.filter(competition=competition, user=request.user).first()

    # Check if the user has already submitted an entry for this competition
    if entry:
        messages.error(request, "क्षमा करें, आप केवल एक बार ही सबमिट कर सकते हैं।")
        return redirect('competition_detail', competition_id=competition_id)

    if request.method == 'POST':
        form = CompetitionEntryForm(request.POST, request.FILES)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.competition = competition
            entry.user = request.user
            entry.save()
            return redirect('user_submitted_entries_list')
    else:
        form = CompetitionEntryForm()

    return render(request, 'submit_entry.html', {'form': form, 'competition': competition})


@login_required
def add_competition(request):
    if request.method == 'POST':
        form = CompetitionForm(request.POST, request.FILES)
        if form.is_valid():
            competition = form.save(commit=False)
            competition.owner = request.user
            competition.save()
            return redirect('competition_list')
    else:
        if request.user.is_authenticated and (request.user.is_admin or request.user.is_owner):
            form = CompetitionForm()
            return render(request, 'add_competition.html', {'form': form})
        else:
            return redirect('index')



@login_required
def submitted_entries_list(request, competition_id):
    competition = get_object_or_404(Competition, pk=competition_id)
    entries = CompetitionEntry.objects.filter(competition=competition)
    return render(request, 'entries_list.html', {'competition': competition, 'entries': entries})

@login_required
def user_submitted_entries_list(request):
    user = request.user
    entries = CompetitionEntry.objects.filter(user=user)
    return render(request, 'profile.html', {'user': user, 'entries': entries})


@login_required
def actions(request):
    if request.user.is_owner or request.user.is_admin:
        return render(request, 'actions.html')
    else:
        messages.error(request, "You are not authorized to access this page.")
        return redirect('index')