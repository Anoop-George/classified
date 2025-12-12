# farmclassifieds/forms.py

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model

from .models import AdPost, AdImage
from .widgets import MultiFileInput   # Ensure widgets.py exists inside same folder
from .fields import MultiFileField

User = get_user_model()


# ------------------------------
#  USER SIGNUP FORM
# ------------------------------
class PhoneSignupForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'maxlength': 4}),
        label="4-digit PIN"
    )

    class Meta:
        model = User
        fields = ['phone_number']
        widgets = {
            'phone_number': forms.TextInput(attrs={'placeholder': 'Phone number'}),
        }

    def clean_password(self):
        pwd = self.cleaned_data['password']
        if not pwd.isdigit() or len(pwd) != 4:
            raise forms.ValidationError("Password must be a 4-digit number.")
        return pwd

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['phone_number']
        user.set_password(self.cleaned_data['password'])
        user.is_active = True
        if commit:
            user.save()
        return user


# ------------------------------
#  LOGIN FORM (PHONE AS USERNAME)
# ------------------------------
class PhoneLoginForm(AuthenticationForm):
    username = forms.CharField(label="Phone number")


# ------------------------------
#  AD POST FORM
# ------------------------------
class AdPostForm(forms.ModelForm):
    images = MultiFileField(
        widget=MultiFileInput(attrs={'multiple': True}),
        required=False
    )

    class Meta:
        model = AdPost
        fields = [
            'title', 'contents', 'category',
            'phone_number', 'postcode', 'district'
        ]

    def clean_images(self):
        files = self.files.getlist('images') if hasattr(self.files, "getlist") else []
            
        if len(files) > 6:
            raise forms.ValidationError("You can upload up to 6 images.")

        return files

    def save(self, commit=True, user=None):
        post = super().save(commit=False)

        if user:
            post.created_by = user

        if commit:
            post.save()

            images = self.cleaned_data.get('images') or []

            for img in images:
                AdImage.objects.create(post=post, image=img)

        return post