from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone

from eval.constants import MAX_UPLOADS_PER_DAY


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_verified", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        verbose_name="email address",
        max_length=255,
        unique=True,
        help_text="Please use your university/organization mail address.",
    )

    university = models.CharField(
        verbose_name="University/Organization", max_length=100
    )
    website = models.URLField(verbose_name="Personal website", blank=True, null=True)
    description = models.TextField(
        verbose_name="Description",
        max_length=1000,
        help_text="Please provide a brief justification of why you need access to the benchmark.",
    )
    is_active = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["university", "website", "description"]

    def __str__(self):
        return self.email

    def maildomain(self):
        return self.email.split("@")[-1]

    def can_upload(self):
        # A user can always upload if they are a superuser, else they must:
        #   1) Be verified (email is checked)
        #   2) Be active (maybe they were deactivated by an admin)
        #   3) Not have submitted too many times in the last 24h
        # Note: We consider all uploads for this, not just active (un-deleted) ones 
        #   as otherwise users can DDoS the server by uploading and deleting repeatedly. 
        date_from = timezone.now() - timezone.timedelta(days=1)
        return self.is_superuser or (
            self.is_verified
            and self.is_active
            and len(
                self.reconstructionentry_set.filter(
                    pub_date__gte=date_from
                )
            )
            < MAX_UPLOADS_PER_DAY
        )

    @property
    def is_staff(self):
        return self.is_superuser
