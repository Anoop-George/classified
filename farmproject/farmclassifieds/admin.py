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
        'is_active',
        'is_staff',
    )

    list_filter = ('is_active', 'is_staff')
    search_fields = ('username', 'phone_number')

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Ad Settings', {
            'fields': ('phone_number', 'ad_post_limit'),
        }),
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
