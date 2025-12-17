from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, AdPost, AdImage


# =========================
# USER ADMIN
# =========================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username',
        'phone_number',
        'ad_post_limit',
        'is_verified_seller',
        'is_active',
    )
    list_editable = ('is_verified_seller', 'ad_post_limit')

    def save_model(self, request, obj, form, change):
        was_verified = False

        if change:
            old = User.objects.get(pk=obj.pk)
            was_verified = old.is_verified_seller

        super().save_model(request, obj, form, change)

        # ✅ USER JUST GOT VERIFIED → AUTO-APPROVE POSTS
        if not was_verified and obj.is_verified_seller:
            AdPost.objects.filter(
                created_by=obj,
                admin_verified=False
            ).update(
                admin_verified=True,
                public_flagged=False
            )

# =========================
# AD IMAGE INLINE
# =========================
class AdImageInline(admin.TabularInline):
    model = AdImage
    extra = 0
    readonly_fields = ('image', 'webp_image')


# =========================
# AD POST ADMIN (SINGLE!)
# =========================
@admin.register(AdPost)
class AdPostAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'created_by',
        'category',
        'district',
        'admin_verified',
        'created_at',
    )

    list_filter = (
        'admin_verified',
        'category',
        'district',
    )

    search_fields = (
        'title',
        'created_by__phone_number',
    )

    list_editable = ('admin_verified',)
    ordering = ('-created_at',)

    inlines = [AdImageInline]


# =========================
# AD IMAGE ADMIN
# =========================
@admin.register(AdImage)
class AdImageAdmin(admin.ModelAdmin):
    list_display = ('post', 'image')
