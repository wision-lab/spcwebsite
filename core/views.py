from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django.views.generic.edit import FormView

from eval.models import EntryVisibility, ReconstructionEntry

from .forms import UserCreationForm


def send_confirmation_email(request, user=None):
    current_site = get_current_site(request)
    mail_subject = "Please confirm your benchmark account"
    user = request.user if not user else user
    message = render_to_string(
        "registration/confirm_email.html",
        {
            "domain": current_site.domain,
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": AccountActivationTokenGenerator().make_token(user),
        },
    )
    send_mail(mail_subject, message, from_email=None, recipient_list=[user.email])


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return str(user.pk) + str(timestamp) + str(user.is_active)


class SignupView(FormView):
    template_name = "registration/signup.html"
    success_url = reverse_lazy("core:confirm")
    form_class = UserCreationForm

    def form_valid(self, form):
        # save form in the memory not in database
        user = form.save(commit=False)
        user.is_verified = False
        user.is_active = True
        user.save()

        send_confirmation_email(self.request, user)
        return super().form_valid(form)


class ResendView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        send_confirmation_email(request)
        return redirect("/")


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_user_model().objects.get(pk=uid)

        if AccountActivationTokenGenerator().check_token(user, token):
            user.is_verified = True
            user.save()
            return render(request, "registration/confirm_successful.html")
    except (TypeError, ValueError, OverflowError, request.user.DoesNotExist):
        pass
    return render(request, "registration/confirm_error.html")


@login_required
def userindex(request):
    entries_list = ReconstructionEntry.objects.filter(
        creator__exact=request.user.pk, is_active=True
    ).order_by("-pub_date")
    context = {"entries_list": entries_list}
    return render(request, "userindex.html", context)


def forward_auth_check(
    request, entry_type=None, user_pk=None, entry_uuid=None, **kwargs
):
    entry_model = {"reconstruction": ReconstructionEntry}.get(entry_type)

    if entry_model is None:
        raise Http404(f"Entry type {entry_type} does not exist.")

    obj = get_object_or_404(entry_model, uuid=entry_uuid, is_active=True)

    if obj.visibility != EntryVisibility.PRIV or (
        request.user.is_authenticated and user_pk == obj.creator.pk
    ):
        # If debug, we can just serve the file directly
        # this should not be used in prod, nor in debug really
        # since the /auth/check endpoint won't be redirected to
        if settings.DEBUG:
            return redirect(request.path.replace("/auth/check/", "/media/"))

        # If a 200-ok is sent back, caddy will serve the file
        return HttpResponse(status=200)

    # Otherwise user is unauthorized!
    return HttpResponse(status=401)
