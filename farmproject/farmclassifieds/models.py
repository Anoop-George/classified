from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image
import os
from django.utils import timezone
from datetime import timedelta


# ------------------------------
#  CUSTOM USER
# ------------------------------
class User(AbstractUser):
    phone_number = models.CharField(max_length=15, unique=True)
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    facebook_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    email = models.EmailField(blank=True, null=True)
    ad_post_limit = models.PositiveIntegerField(default=3)
    is_verified_seller = models.BooleanField(default=False)
    
    def __str__(self):
        return self.username or self.phone_number

    @property
    def number_of_adposts(self):
        # Correct reverse relation
        return self.posts.count()


# ------------------------------
#  AD POST
# ------------------------------
# models.py (ONLY AdPost part)

from datetime import timedelta
from django.utils import timezone

class AdPost(models.Model):
    CATEGORY_CHOICES = [
        ('fish', 'Fish'),
        ('chicken', 'Chicken'),
        ('duck', 'Duck'),
        ('other_birds', 'Other Birds'),
        ('cow', 'Cow'),
        ('goat', 'Goat'),
        ('buffalo', 'Buffalo'),
        ('agri_produce', 'Agri Produce'),
        ('seeds', 'Seeds'),
        ('dogs', 'Dogs'),
        ('cats', 'Cats'),
        ('equipment', 'Equipment'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=200)
    contents = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    phone_number = models.CharField(max_length=20)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
        null=True,
        blank=True
    )

    postcode = models.CharField(max_length=20)
    district = models.CharField(max_length=100)

    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    view_count = models.PositiveIntegerField(default=0)
    admin_verified = models.BooleanField(default=False)
    public_flagged = models.BooleanField(default=False)

    expires_at = models.DateTimeField()
    renew_count = models.PositiveIntegerField(default=0)
    is_expired = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Set expiry ONLY on first creation
        if not self.pk and not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=60)

        # Keep is_expired in sync
        self.is_expired = timezone.now() > self.expires_at

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# ------------------------------
#  AD IMAGE (with compression + WebP)
# ------------------------------
def get_image_upload_path(instance, filename):
    return os.path.join('ad_images', filename)


def get_webp_upload_path(instance, filename):
    return os.path.join('ad_images', 'webp', filename)

# ------------------------------
#  AD IMAGE (with hard limit: max 6 images per post)
# ------------------------------

class AdImage(models.Model):
    post = models.ForeignKey(
        AdPost,
        on_delete=models.CASCADE,
        related_name='images'
    )

    image = models.ImageField(upload_to=get_image_upload_path)
    webp_image = models.ImageField(
        upload_to=get_webp_upload_path,
        blank=True,
        null=True
    )

    def __str__(self):
        return f"Image for post {self.post_id}"

    def save(self, *args, **kwargs):
        # Enforce MAX 6 images per post at model-level
        if self.post.images.count() >= 6:
            raise ValueError("A post cannot have more than 6 images.")

        raw = kwargs.pop('raw', False)

        if self.image and not raw:
            img = Image.open(self.image)
            img = img.convert('RGB')

            # -------- Compressed JPEG ----------
            jpg_io = BytesIO()
            img.save(jpg_io, format='JPEG', quality=75, optimize=True)
            jpg_io.seek(0)

            base_name, _ext = os.path.splitext(self.image.name)
            jpg_name = base_name + ".jpg"
            self.image.save(jpg_name, ContentFile(jpg_io.getvalue()), save=False)

            # -------- WebP variant -------------
            try:
                webp_io = BytesIO()
                img.save(webp_io, format='WEBP', quality=70, method=6)
                webp_io.seek(0)
                webp_name = base_name + ".webp"
                self.webp_image.save(webp_name, ContentFile(webp_io.getvalue()), save=False)
            except OSError:
                pass

        super().save(*args, **kwargs)
