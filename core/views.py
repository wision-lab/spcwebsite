from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import (
    PasswordResetTokenGenerator,
    default_token_generator,
)
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django.views.generic.edit import FormView

from eval.models import ReconstructionEntry

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
    success_url = "/accounts/confirm"
    form_class = UserCreationForm

    def form_valid(self, form):
        # save form in the memory not in database
        user = form.save(commit=False)
        user.is_verified = False
        user.is_active = True
        user.save()

        send_confirmation_email(self.request, user)


class Resend(LoginRequiredMixin, View):
    def post(self, request):
        send_confirmation_email(request)
        return redirect("/")


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_user_model().objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        user = None
    if user is not None and AccountActivationTokenGenerator().check_token(user, token):
        user.is_verified = True
        user.save()
        return render(request, "registration/confirm_successful.html")
    else:
        return render(request, "registration/confirm_error.html")


@login_required
def userindex(request):
    entries_list = ReconstructionEntry.objects.filter(
        creator__exact=request.user.pk
    ).order_by("pub_date")
    context = {"entries_list": entries_list}
    return render(request, "userindex.html", context)
