from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import *

class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, help_text='Enter your email')
    phone_no = forms.CharField(max_length=15, help_text='Enter your phone number')

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'phone_no', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email address already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username

    def clean_phone_no(self):
        phone_no = self.cleaned_data.get('phone_no')
        if CustomUser.objects.filter(phone_no=phone_no).exists():
            raise forms.ValidationError("A user with that phone number already exists.")
        return phone_no

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['name', 'bio', 'place', 'profile_image']

class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(label='Current Password', widget=forms.PasswordInput)
    new_password = forms.CharField(label='New Password', widget=forms.PasswordInput)
    confirm_new_password = forms.CharField(label='Confirm New Password', widget=forms.PasswordInput)

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name_en', 'name_hi']


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'description', 'category']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter post title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter post description'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.fields['category'].choices = [(category.id, f"{category.name_hi}") for category in Category.objects.all()]


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']




class CompetitionEntryForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(), 
        empty_label=None,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = CompetitionEntry
        fields = ['post_title', 'post_description', 'category']
        widgets = {
            'post_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter post title'}),
            'post_description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter post description'}),
        }

    def __init__(self, *args, **kwargs):
        super(CompetitionEntryForm, self).__init__(*args, **kwargs)
        self.fields['category'].choices = [(category.id, category.name_hi) for category in Category.objects.all()]

class CompetitionForm(forms.ModelForm):
    class Meta:
        model = Competition
        fields = ['title', 'description', 'start_date', 'end_date', 'image', 'rules']
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }



class CarouselItemForm(forms.ModelForm):
    class Meta:
        model = CarouselItem
        fields = ['image', 'url']
        
        
        
class PostSearchForm(forms.Form):
    query = forms.CharField(label='Search', max_length=100, required=False)
        