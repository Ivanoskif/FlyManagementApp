from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from .forms import SignUpForm, ProfileForm
from .models import PassengerProfile
from accounts.forms import DemoPaymentForm
from accounts.services.services_memberships import upgrade_membership
from django.core.exceptions import ValidationError

# Create your views here.

def signup(request):
    form = SignUpForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("core:home")

    return render(request, "accounts/signup.html", {"form": form})

@login_required
def profile(request):
    profile, _ = PassengerProfile.objects.get_or_create(
        user=request.user,
        defaults={
            "first_name": request.user.first_name or "",
            "last_name": request.user.last_name or "",
        },
    )

    form = ProfileForm(request.POST or None, instance=profile, user=request.user)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated successfully.")
        return redirect("accounts:profile")

    return render(request, "accounts/profile.html", {"form": form})

@login_required
def membership_page(request):
    if not request.user.groups.filter(name="Passenger").exists():
        messages.error(request, "This page is for passengers only.")
        return redirect("core:home")

    profile, _ = PassengerProfile.objects.get_or_create(
        user=request.user,
        defaults={"first_name": request.user.first_name or "", "last_name": request.user.last_name or ""},
    )

    return render(
        request,
        "accounts/membership.html",
        {
            "profile": profile,
            "levels": PassengerProfile.MembershipLevel,
        },
    )


@login_required
def membership_upgrade(request):
    if not request.user.groups.filter(name="Passenger").exists():
        messages.error(request, "This action is for passengers only")
        return redirect("core:home")

    profile, _ = PassengerProfile.objects.get_or_create(
        user=request.user,
        defaults={"first_name": request.user.first_name or "", "last_name": request.user.last_name or ""},
    )

    target = request.GET.get("level") or request.POST.get("level")
    if not target:
        messages.error(request, "Missing membership level")
        return redirect("accounts:membership")

    valid_levels = {c[0] for c in PassengerProfile.MembershipLevel.choices}
    if target not in valid_levels:
        messages.error(request, "Invalid membership level.")
        return redirect("accounts:membership")

    form = DemoPaymentForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            provider_ref = f"DEMO-MEM-{request.user.id}-{target}"
            upgrade_membership(user=request.user, target_level=target, provider_ref=provider_ref)
            messages.success(request, f"Membership upgraded to {target}.")
            return redirect("accounts:membership")
        except ValidationError as ex:
            messages.error(request, ex.message)

    return render(
        request,
        "accounts/membership_upgrade.html",
        {"profile": profile, "target": target, "form": form},
    )