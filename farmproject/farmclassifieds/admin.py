from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone

from .models import User, AdPost, AdImage
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse
from django.utils.html import format_html


# =========================
# USER ADMIN
# =========================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "id",
        "username",
        "phone_number",
        "ad_post_limit",
        "is_verified_seller",
        "is_active",
        "is_staff",
    )

    list_editable = (
        "ad_post_limit",
        "is_verified_seller",
    )

    search_fields = (
        "id",
        "username",
        "phone_number",
    )

    ordering = ("-date_joined",)

    def save_model(self, request, obj, form, change):
        was_verified = False

        if change:
            old = User.objects.get(pk=obj.pk)
            was_verified = old.is_verified_seller

        super().save_model(request, obj, form, change)

        # ✅ USER JUST GOT VERIFIED → AUTO-APPROVE THEIR PENDING POSTS
        if not was_verified and obj.is_verified_seller:
            AdPost.objects.filter(
                created_by=obj,
                admin_verified=False
            ).update(
                admin_verified=True,
                public_flagged=False
            )


# =========================
# AD IMAGE INLINE (POST PAGE)
# =========================
class AdImageInline(admin.TabularInline):
    model = AdImage
    extra = 0
    readonly_fields = ("image", "webp_image")


# =========================
# AD POST ADMIN
# =========================
@admin.register(AdPost)
class AdPostAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "created_by",
        "phone_number",
        "category",
        "district",
        "postcode",
        "admin_verified",
        "public_flagged",
        "expires_at",
        "view_count",
        "created_at",
         "expires_at",
        "is_currently_expired",
    )

    list_filter = (
        "admin_verified",
        "public_flagged",
        "category",
        "district",
        "expires_at",
    )

    search_fields = (
        "id",                      # 🔥 Search by Ad ID
        "title",
        "phone_number",
        "postcode",
        "district",
        "created_by__phone_number",
        "created_by__username",
    )

    list_editable = ("admin_verified",)

    ordering = ("-created_at",)

    readonly_fields = (
        "view_count",
        "created_at",
        "modified_at",
    )

    autocomplete_fields = ("created_by",)

    inlines = [AdImageInline]

    # Optional: highlight expired ads
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("created_by")
    def is_currently_expired(self, obj):
        return obj.expires_at <= timezone.now()
    is_currently_expired.boolean = True
    is_currently_expired.short_description = "Expired?"


# =========================
# AD IMAGE ADMIN (STANDALONE)
# =========================
@admin.register(AdImage)
class AdImageAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "image")
    autocomplete_fields = ("post",)


