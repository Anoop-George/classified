# farmclassifieds/views.py

from datetime import timedelta

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


# ---------------------------------------------
# PUBLIC LIST VIEW
# ---------------------------------------------
def post_list(request):
    posts = (
        AdPost.objects
        .filter(admin_verified=True)
        .prefetch_related("images")   # ✅ CRITICAL FIX
        .order_by("-created_at")
    )

    query = request.GET.get("q", "")
    if query:
        posts = posts.filter(
            Q(title__icontains=query) |
            Q(contents__icontains=query) |
            Q(postcode__icontains=query) |
            Q(district__icontains=query)
        )

    posts = posts[:15]  # slice AFTER prefetch

    return render(request, "post_list.html", {
        "posts": posts,
        "query": query,
    })


# ---------------------------------------------
# FILTERED VIEW
# ---------------------------------------------
def filtered_view(request):
    posts = AdPost.objects.filter(admin_verified=True).order_by('-created_at')

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
def post_detail(request, pk):
    post = get_object_or_404(AdPost, pk=pk)

    # Public cannot see unverified posts
    if not post.admin_verified and not request.user.is_staff:
        return HttpResponseNotFound("This post is not available.")

    # ✅ Increment view count ONLY on GET + only when verified
    if request.method == "GET" and post.admin_verified:
        AdPost.objects.filter(pk=pk).update(view_count=F("view_count") + 1)
        # refresh so template shows updated number (optional)
        post.refresh_from_db(fields=["view_count"])

    # ✅ Handle spam report ONLY on POST
    if request.method == "POST" and "report_spam" in request.POST:
        if not post.public_flagged:
            post.public_flagged = True
            post.save(update_fields=["public_flagged"])

        messages.success(
            request,
            "Thank you. This post has been reported and will be reviewed by an administrator."
        )
        # ✅ redirect ONLY after POST (prevents repeat form resubmit)
        return redirect("post_detail", pk=pk)

    url = request.build_absolute_uri()

    return render(request, "post_detail.html", {
        "post": post,
        "share_facebook": f"https://www.facebook.com/sharer/sharer.php?u={url}",
        "share_whatsapp": f"https://wa.me/?text={url}",
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
            form.save(user=user)
            messages.success(request, "Your ad has been submitted for admin approval.")
            return redirect('my_posts')
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
    posts = AdPost.objects.filter(created_by=request.user).order_by('-created_at')

    for p in posts:
        p.renew_left = max(0, 3 - p.renew_count)

    return render(request, 'my_posts.html', {'posts': posts})


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
@login_required
def renew_post(request, pk):
    post = get_object_or_404(AdPost, pk=pk, created_by=request.user)

    if post.renew_count >= 3:
        messages.error(request, "Renewal limit reached. Please contact administrator.")
        return redirect('my_posts')

    post.expires_at += timedelta(days=60)
    post.renew_count += 1
    post.is_expired = False
    post.save(update_fields=["expires_at", "renew_count", "is_expired"])

    messages.success(request, "Your ad has been renewed for 2 more months.")
    return redirect('my_posts')


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

    post.expires_at += timedelta(days=60)
    post.is_expired = False
    post.save(update_fields=["expires_at", "is_expired"])

    messages.success(request, "Ad extended by 2 months.")
    return redirect('admin_verification')
