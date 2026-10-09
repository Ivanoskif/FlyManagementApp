from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden


def operator_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.user.is_superuser or request.user.is_staff:
            return view_func(request, *args, **kwargs)
        if request.user.groups.filter(name="Operator").exists():
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Forbidden")
    return _wrapped
