from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Q
from django.http import HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PhoneSignupForm, PhoneLoginForm, AdPostForm
from .models import AdPost


# ------------------------------
#  PUBLIC LIST VIEWS
# ------------------------------
def post_list(request):
    """
    General view:
    - list 15 most recent verified posts
    - supports search by title/contents/postcode/district
    """
    posts = AdPost.objects.filter(admin_verified=True).order_by('-created_at')

    query = request.GET.get('q', '')
    if query:
        posts = posts.filter(
            Q(title__icontains=query)
            | Q(contents__icontains=query)
            | Q(postcode__icontains=query)
            | Q(district__icontains=query)
        )

    posts = posts[:15]

    context = {
        'posts': posts,
        'query': query,
    }
    return render(request, 'post_list.html', context)


def filtered_view(request):
    """
    Filtered view:
    - filter by postcode, category, district
    """
    posts = AdPost.objects.filter(admin_verified=True).order_by('-created_at')

    postcode = request.GET.get('postcode') or ''
    category = request.GET.get('category') or ''
    district = request.GET.get('district') or ''

    if postcode:
        posts = posts.filter(postcode__icontains=postcode)
    if category:
        posts = posts.filter(category=category)
    if district:
        posts = posts.filter(district__icontains=district)

    context = {
        'posts': posts,
        'postcode': postcode,
        'category': category,
        'district': district,
    }
    return render(request, 'post_list.html', context)


# ------------------------------
#  POST DETAIL
# ------------------------------
def post_detail(request, pk):
    """
    Detail view:
    - Public can only see admin_verified posts
    - Admin/staff can see unverified posts as preview
    - Shows images, contact, view count, share buttons
    """
    post = get_object_or_404(AdPost, pk=pk)

    # Public should not see unverified posts
    if not post.admin_verified and not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseNotFound("This post is not available.")

    # Only count views for verified posts
    if post.admin_verified:
        AdPost.objects.filter(pk=pk).update(view_count=post.view_count + 1)

    if request.method == 'POST' and 'report_spam' in request.POST:
        post.public_flagged = True
        post.save()
        messages.success(request, "Thank you for reporting this post.")
        return redirect('post_detail', pk=pk)

    url = request.build_absolute_uri()
    context = {
        'post': post,
        'share_facebook': f"https://www.facebook.com/sharer/sharer.php?u={url}",
        'share_whatsapp': f"https://wa.me/?text={url}",
        'share_instagram': url,  # No official web share URL, just share the link
    }
    return render(request, 'post_detail.html', context)


# ------------------------------
#  CREATE POST
# ------------------------------
@login_required
def post_create(request):
    """
    Create new ad post.
    - User must be logged in
    - Respects ad_post_limit on User
    """
    user = request.user
    if user.number_of_adposts >= user.ad_post_limit:
        messages.error(request, "You have reached your ad posting limit.")
        return redirect('post_list')

    if request.method == 'POST':
        form = AdPostForm(request.POST, request.FILES)
        if form.is_valid():
            form.save(user=user)
            messages.success(
                request,
                "Post submitted successfully. It will be visible after admin verification."
            )
            return redirect('post_list')
    else:
        form = AdPostForm()

    return render(request, 'post_form.html', {'form': form})


# ------------------------------
#  ADMIN VERIFICATION
# ------------------------------
def is_staff_or_superuser(user):
    return user.is_staff or user.is_superuser


@user_passes_test(is_staff_or_superuser)
def admin_verification_list(request):
    """
    Admin view:
    - list all unverified posts (pending)
    - list all public-flagged posts
    - approve = set admin_verified=True
    - reject = delete post
    """
    new_posts = AdPost.objects.filter(admin_verified=False)
    flagged_posts = AdPost.objects.filter(public_flagged=True)

    if request.method == 'POST':
        action = request.POST.get('action')
        post_id = request.POST.get('post_id')
        post = get_object_or_404(AdPost, pk=post_id)

        if action == 'approve':
            post.admin_verified = True
            post.public_flagged = False
            post.save()
            messages.success(request, "Post approved.")
        elif action == 'reject':
            post.delete()
            messages.success(request, "Post rejected and deleted.")
        return redirect('admin_verification_list')

    context = {
        'new_posts': new_posts,
        'flagged_posts': flagged_posts,
    }
    return render(request, 'admin_verification_list.html', context)


# ------------------------------
#  AUTH VIEWS
# ------------------------------
def signup_view(request):
    """
    Signup with phone number + 4-digit PIN.
    """
    if request.method == 'POST':
        form = PhoneSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Signup successful.")
            return redirect('post_list')
    else:
        form = PhoneSignupForm()
    return render(request, 'signup.html', {'form': form})


class PhoneLoginView(LoginView):
    """
    Login using phone as username.
    """
    authentication_form = PhoneLoginForm
    template_name = 'login.html'
