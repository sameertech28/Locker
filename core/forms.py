from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from .models import Group, Profile, VaultFile

class CustomLoginForm(AuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            user_exists = User.objects.filter(username=username).exists() or User.objects.filter(email=username).exists()
            if not user_exists:
                raise forms.ValidationError("This email/username is not registered.")
                
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                raise forms.ValidationError("Incorrect password.")
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    full_name = forms.CharField(required=True, max_length=150, label="Full name")

    class Meta:
        model = User
        fields = ["username", "email", "full_name", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        name_parts = self.cleaned_data["full_name"].split(" ", 1)
        user.first_name = name_parts[0]
        user.last_name = name_parts[1] if len(name_parts) > 1 else ""
        if commit:
            user.save()
        return user


class VaultFileUploadForm(forms.ModelForm):
    class Meta:
        model = VaultFile
        fields = ["file", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2, "placeholder": "Add a description (optional)"}),
        }

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if not file:
            return file

        # Limit file size to 50MB
        max_size_mb = 50
        if file.size > max_size_mb * 1024 * 1024:
            raise forms.ValidationError(f"File size cannot exceed {max_size_mb}MB.")

        # Block malicious extensions
        blocked_extensions = [".php", ".exe", ".sh", ".bat", ".pl", ".cgi", ".py"]
        import os
        ext = os.path.splitext(file.name)[1].lower()
        if ext in blocked_extensions:
            raise forms.ValidationError("This file type is not allowed for security reasons.")

        return file


class VaultFileEditForm(forms.ModelForm):
    class Meta:
        model = VaultFile
        fields = ["file_name", "description", "tags"]


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ["name", "description", "cover_image", "is_private", "max_members"]


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)

    class Meta:
        model = Profile
        fields = ["avatar", "theme_preference"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields["first_name"].initial = self.user.first_name
            self.fields["last_name"].initial = self.user.last_name

    def save(self, commit=True):
        profile = super().save(commit=commit)
        if self.user:
            self.user.first_name = self.cleaned_data.get("first_name", "")
            self.user.last_name = self.cleaned_data.get("last_name", "")
            if commit:
                self.user.save()
        return profile
