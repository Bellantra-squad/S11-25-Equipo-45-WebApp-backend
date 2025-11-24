
from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.db.models import EmailField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    """
    Default custom user model for CRM.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    email = EmailField(_("email address"), unique=True)
    password_hash = CharField(_("password hash"), max_length=255, editable=False)
    first_name = CharField(_("first name"), max_length=150, blank=True)
    last_name = CharField(_("last name"), max_length=150, blank=True)
    role = CharField(_("role"), max_length=50, blank=True)
    username = None  # type: ignore[assignment]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})

    def save(self, *args, **kwargs):
        """Override save to store password hash."""
        if hasattr(self, 'password') and self.password:
            # Get the hashed password from the parent class
            super().save(*args, **kwargs)
            self.password_hash = self.password
            if self.pk:
                # Update only password_hash to avoid re-hashing
                User.objects.filter(pk=self.pk).update(password_hash=self.password)
        else:
            super().save(*args, **kwargs)
