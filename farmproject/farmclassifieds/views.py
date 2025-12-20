# farmclassifieds/views.py

from datetime import timedelta
from django.utils import timezone  # add this import

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Q, F
from django.http import HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PhoneSignupForm, PhoneLoginForm, AdPostForm
from .models import AdPost, User
from django.db.models import Prefetch
from .models import AdPost, AdImage


# ---------------------------------------------
# PUBLIC LIST VIEW
# ---------------------------------------------
from django.db.models import Prefetch
from .models import AdPost, AdImage

def post_list(request):
    posts = (
        AdPost.objects
        .filter(admin_verified=True, expires_at__gt=timezone.now())
        .prefetch_related(
            Prefetch(
                "images",
                queryset=AdImage.objects.only("image", "webp_image")
            )
        )
    )

    # -----------------------
    # FILTERS (OPTIONAL)
    # -----------------------
    district = request.GET.get("district")
    category = request.GET.get("category")
    postcode = request.GET.get("postcode")

    if district:
        posts = posts.filter(district__iexact=district)

    if category:
        posts = posts.filter(category=category)

    if postcode:
        posts = posts.filter(postcode__icontains=postcode)

    # -----------------------
    # SORTING
    # -----------------------
    sort = request.GET.get("sort", "new")

    if sort == "price_low":
        posts = posts.order_by("price")
    elif sort == "price_high":
        posts = posts.order_by("-price")
    elif sort == "old":
        posts = posts.order_by("created_at")
    else:
        posts = posts.order_by("-created_at")  # default newest

    # -----------------------
    # FILTER OPTIONS
    # -----------------------
    districts = (
        AdPost.objects
        .filter(admin_verified=True)
        .values_list("district", flat=True)
        .distinct()
        .order_by("district")
    )

    categories = AdPost.CATEGORY_CHOICES

    return render(request, "post_list.html", {
        "posts": posts,
        "districts": districts,
        "categories": categories,
        "selected_district": district,
        "selected_category": category,
        "selected_postcode": postcode,
        "selected_sort": sort,
    })



# ---------------------------------------------
# FILTERED VIEW
# ---------------------------------------------
def filtered_view(request):
    posts = AdPost.objects.filter(admin_verified=True,expires_at__gt=timezone.now(),
).order_by('-created_at')

    postcode = request.GET.get('postcode', '')
    category = request.GET.get('category', '')
    district = request.GET.get('district', '')

    if postcode:
        posts = posts.filter(postcode__icontains=postcode)
    if category:
        posts = posts.filter(category=category)
    if district:
        posts = posts.filter(district__icontains=district)

    return render(request, 'post_list.html', {
        'posts': posts,
        'postcode': postcode,
        'category': category,
        'district': district
    })


# ---------------------------------------------
# POST DETAIL VIEW  ✅ FIXED (NO redirect loop)
# ---------------------------------------------
from django.db.models import F
from django.http import HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

def post_detail(request, pk):
    post = get_object_or_404(AdPost, pk=pk)

    # ❌ Public users cannot see unverified posts
    if not post.admin_verified and not request.user.is_staff:
        return HttpResponseNotFound("This post is not available.")
    if post.expires_at <= timezone.now() and not request.user.is_staff:
        return HttpResponseNotFound("This post has expired.")
    # ----------------------------------
    # ✅ SAFE VIEW COUNT (session-based)
    # ----------------------------------
    session_key = f"viewed_post_{post.pk}"

    if request.method == "GET" and post.admin_verified:
        if not request.session.get(session_key):
            AdPost.objects.filter(pk=post.pk).update(
                view_count=F("view_count") + 1
            )
            request.session[session_key] = True
            post.refresh_from_db(fields=["view_count"])

    # ----------------------------------
    # 🚩 REPORT SPAM (POST only)
    # ----------------------------------
    if request.method == "POST" and "report_spam" in request.POST:
        if not post.public_flagged:
            post.public_flagged = True
            post.save(update_fields=["public_flagged"])

        messages.success(
            request,
            "Thank you. This post has been reported and will be reviewed by an administrator."
        )
        return redirect("post_detail", pk=pk)

    # ----------------------------------
    # 🔗 SHARE LINKS
    # ----------------------------------
    url = request.build_absolute_uri()

    whatsapp_text = (
        f"{post.title}\n"
        f"Location: {post.district}\n\n"
        f"View details:\n{url}"
    )

    return render(request, "post_detail.html", {
        "post": post,
        "share_facebook": f"https://www.facebook.com/sharer/sharer.php?u={url}",
        "share_whatsapp": f"https://wa.me/?text={whatsapp_text}",
        "share_instagram": url,
    })


# ---------------------------------------------
# CREATE POST
# ---------------------------------------------
@login_required
def post_create(request):
    user = request.user

    # Admin bypass
    if not user.is_staff:
        if user.posts.count() >= user.ad_post_limit:
            messages.error(
                request,
                f"You have reached your ad limit ({user.ad_post_limit}). "
                "Please contact the administrator to post more ads."
            )
            return redirect('my_posts')

    if request.method == 'POST':
        form = AdPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False, user=request.user)

    # ✅ AUTO-APPROVAL LOGIC
        if request.user.is_verified_seller:
            post.admin_verified = True
        else:
            post.admin_verified = False

        post.save()
        form.save_m2m()

        messages.success(
            request,
            "Post published successfully"
            if post.admin_verified
            else "Post submitted for admin approval"
        )

        return redirect("my_posts")

    else:
        form = AdPostForm()

    return render(request, 'post_form.html', {'form': form})


# ---------------------------------------------
# SIGNUP
# ---------------------------------------------
def signup_view(request):
    if request.method == "POST":
        form = PhoneSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Signup successful.")
            return redirect("post_list")
    else:
        form = PhoneSignupForm()

    return render(request, "signup.html", {"form": form})


# ---------------------------------------------
# LOGIN VIEW
# ---------------------------------------------
class PhoneLoginView(LoginView):
    authentication_form = PhoneLoginForm
    template_name = "login.html"


# ---------------------------------------------
# MY POSTS
# ---------------------------------------------
@login_required
def my_posts(request):
    posts = AdPost.objects.filter(created_by=request.user).order_by("-created_at")

    for post in posts:
        post.renew_left = max(0, 3 - post.renew_count)

    return render(request, "my_posts.html", {
        "posts": posts
    })


# ------------------------------
# EDIT POST
# ------------------------------
@login_required
def post_edit(request, pk):
    post = get_object_or_404(AdPost, pk=pk, created_by=request.user)

    if request.method == 'POST':
        form = AdPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save(user=request.user)
            messages.success(request, "Post updated successfully.")
            return redirect('my_posts')
    else:
        form = AdPostForm(instance=post)

    return render(request, 'post_edit.html', {'form': form, 'post': post})


# ------------------------------
# DELETE POST
# ------------------------------
@login_required
def post_delete(request, pk):
    post = get_object_or_404(AdPost, pk=pk, created_by=request.user)

    if request.method == 'POST':
        post.delete()
        messages.success(request, "Post deleted successfully.")
        return redirect('my_posts')

    return render(request, 'post_delete_confirm.html', {'post': post})


# ---------------------------------------------
# ADMIN VERIFICATION PANEL
# ---------------------------------------------
@staff_member_required
def admin_verification(request):
    posts = AdPost.objects.filter(admin_verified=False, public_flagged=False)
    flagged_posts = AdPost.objects.filter(public_flagged=True)

    return render(request, "admin_verification.html", {
        "posts": posts,
        "flagged_posts": flagged_posts,
    })


@staff_member_required
def admin_approve_post(request, pk):
    post = get_object_or_404(AdPost, pk=pk)
    post.admin_verified = True
    post.public_flagged = False  # ✅ clear spam flag when approving
    post.save(update_fields=["admin_verified", "public_flagged"])

    messages.success(request, "Post approved and cleared from spam reports.")
    return redirect("admin_verification")


@staff_member_required
def admin_reject_post(request, pk):
    post = get_object_or_404(AdPost, pk=pk)
    post.delete()
    messages.warning(request, "Post rejected and deleted.")
    return redirect('admin_verification')


@staff_member_required
def admin_delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if user.is_superuser:
        messages.error(request, "Superusers cannot be deleted.")
        return redirect('admin_verification')

    if request.method == 'POST':
        user.delete()
        messages.success(request, "User and all related ads deleted.")
        return redirect('admin_verification')

    return render(request, 'admin_delete_user_confirm.html', {'user': user})


# ---------------------------------------------
# RENEW POST
# ---------------------------------------------
# views.py

@login_required
def renew_post(request, pk):
    post = get_object_or_404(AdPost, pk=pk, created_by=request.user)

    if post.renew_count >= 3:
        messages.error(request, "Renewal limit reached. Contact admin.")
        return redirect("my_posts")

    post.expires_at += timedelta(days=60)
    post.renew_count += 1
    post.is_expired = False

    post.save(update_fields=["expires_at", "renew_count", "is_expired"])

    messages.success(request, "Your ad has been renewed for 2 more months.")
    return redirect("my_posts")


@staff_member_required
def admin_update_ad_limit(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        new_limit = request.POST.get('ad_post_limit', '').strip()
        if new_limit.isdigit():
            user.ad_post_limit = int(new_limit)
            user.save(update_fields=['ad_post_limit'])
            messages.success(request, "Ad limit updated.")

    return redirect('admin_verification')



@staff_member_required
def admin_extend_post(request, pk):
    post = get_object_or_404(AdPost, pk=pk)

    if request.method == "POST":
        months = request.POST.get("months", "2")

        try:
            months = int(months)
        except ValueError:
            months = 2

        post.expires_at += timedelta(days=30 * months)
        post.is_expired = False
        post.save(update_fields=["expires_at", "is_expired"])

        messages.success(
            request,
            f"Ad #{post.pk} extended by {months} month(s)."
        )
        return redirect("admin_verification")

    return render(request, "admin_extend_post.html", {"post": post})





def select_category(request, district):
    categories = (
        AdPost.objects
        .filter(admin_verified=True, district=district, expires_at__gt=timezone.now(),)
        .values_list("category", flat=True)
        .distinct()
    )

    return render(request, "select_category.html", {
        "district": district,
        "categories": categories
    })

def posts_by_location(request, district, category):
    posts = (
        AdPost.objects
        .filter(
            admin_verified=True,
            district=district,
            category=category,
                        expires_at__gt=timezone.now(),

        )
        .prefetch_related(
            Prefetch(
                'images',
                queryset=AdImage.objects.only('image', 'webp_image')
            )
        )
        .order_by('-created_at')
    )

    return render(request, "post_list.html", {
        "posts": posts,
        "district": district,
        "category": category
    })


from django.core.paginator import Paginator
from .models import AdPost


def search_results(request):
    posts = AdPost.objects.filter(admin_verified=True, expires_at__gt=timezone.now())

    # FILTERS
    district = request.GET.get("district")
    category = request.GET.get("category")
    postcode = request.GET.get("postcode")

    if district:
        posts = posts.filter(district=district)

    if category:
        posts = posts.filter(category=category)

    if postcode:
        posts = posts.filter(postcode__icontains=postcode)

    # SORTING
    sort = request.GET.get("sort", "new")

    if sort == "price_low":
        posts = posts.order_by("price")
    elif sort == "price_high":
        posts = posts.order_by("-price")
    elif sort == "old":
        posts = posts.order_by("created_at")
    else:
        posts = posts.order_by("-created_at")

    # PAGINATION
    paginator = Paginator(posts, 10)  # 10 per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "search_results.html", {
        "page_obj": page_obj,
        "sort": sort,
        "request": request,
    })
