# farmclassifieds/views.py

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.http import HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PhoneSignupForm, PhoneLoginForm, AdPostForm
from .models import AdPost


# ---------------------------------------------
# PUBLIC LIST VIEW
# ---------------------------------------------
def post_list(request):
    posts = AdPost.objects.filter(admin_verified=True).order_by('-created_at')

    query = request.GET.get('q', '')
    if query:
        posts = posts.filter(
            Q(title__icontains=query) |
            Q(contents__icontains=query) |
            Q(postcode__icontains=query) |
            Q(district__icontains=query)
        )

    return render(request, 'post_list.html', {
        'posts': posts[:15],
        'query': query
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
# POST DETAIL VIEW
# ---------------------------------------------
def post_detail(request, pk):
    post = get_object_or_404(AdPost, pk=pk)

    # Public cannot see unverified posts
    if not post.admin_verified and not request.user.is_staff:
        return HttpResponseNotFound("This post is not available.")

    # Increase view count only for verified posts
    if post.admin_verified:
        AdPost.objects.filter(pk=pk).update(view_count=post.view_count + 1)

    if request.method == "POST" and "report_spam" in request.POST:
        post.public_flagged = True
        post.save()
        messages.success(request, "Thank you for reporting this post.")
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

    print("DEBUG request.FILES =", request.FILES)

    user = request.user

    # FIX #1 — Correct counting because User.posts does NOT exist
    user_post_count = AdPost.objects.filter(created_by=user).count()

    if user_post_count >= user.ad_post_limit:
        messages.error(request, "You have reached your ad posting limit.")
        return redirect("post_list")

    if request.method == "POST":
        form = AdPostForm(request.POST, request.FILES)

        print("DEBUG files inside form =", request.FILES.getlist("images"))

        if form.is_valid():
            form.save(user=user)
            messages.success(request, "Post submitted successfully. Pending admin approval.")
            return redirect("post_list")
        else:
            print("FORM ERRORS:", form.errors)

    else:
        form = AdPostForm()

    return render(request, "post_form.html", {"form": form})


# ---------------------------------------------
# ADMIN VERIFICATION
# ---------------------------------------------
def is_staff_or_superuser(user):
    return user.is_staff or user.is_superuser


@user_passes_test(is_staff_or_superuser)
def admin_verification_list(request):

    new_posts = AdPost.objects.filter(admin_verified=False)
    flagged_posts = AdPost.objects.filter(public_flagged=True)

    if request.method == "POST":
        post_id = request.POST.get("post_id")
        action = request.POST.get("action")

        post = get_object_or_404(AdPost, pk=post_id)

        if action == "approve":
            post.admin_verified = True
            post.public_flagged = False
            post.save()
            messages.success(request, "Post approved.")

        elif action == "reject":
            post.delete()
            messages.success(request, "Post rejected and deleted.")

        return redirect("admin_verification_list")

    return render(request, "admin_verification_list.html", {
        "new_posts": new_posts,
        "flagged_posts": flagged_posts
    })


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
