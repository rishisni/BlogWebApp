# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    is_admin = models.BooleanField(default=False)
    is_owner = models.BooleanField(default=False)
    phone_no = models.CharField(max_length=15, blank=True, null=True)

    def followers_count(self):
        return self.followers.count()

    def following_count(self):
        return self.following.count()



class Profile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    place = models.CharField(max_length=100, blank=True)
    profile_image = models.ImageField(upload_to='media/profile_images/', blank=True)

    def __str__(self):
        return self.user.username

class Category(models.Model):
    name_en = models.CharField(max_length=100, verbose_name="English Name",unique=True)
    name_hi = models.CharField(max_length=100, verbose_name="Hindi Name",unique=True)

    def __str__(self):
        return self.name_en  # You can change this to return either English or Hindi name

    class Meta:
        verbose_name_plural = "Categories"


class Post(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)  # New field for approval status
    declined = models.BooleanField(default=False) 
    likes = models.ManyToManyField(CustomUser, through='Like', related_name='liked_posts')
    likes_count = models.IntegerField(default=0) 

    def __str__(self):
        return self.title
    
    def update_likes_count(self):
        self.likes_count = self.likes.count()
        self.save()

class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_likes')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.post.update_likes_count()


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Follow(models.Model):
    follower = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='following')
    followee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'followee')  # Ensure unique follow relationships

    def __str__(self):
        return f'{self.follower.username} follows {self.followee.username}'


class Competition(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    image = models.ImageField(upload_to='competition_images/')
    rules = models.TextField()

class CompetitionEntry(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    post_title = models.CharField(max_length=100)
    post_description = models.TextField()
    category = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    


class CarouselItem(models.Model):
    image = models.ImageField(upload_to='carousel_images/')
    url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.image.name