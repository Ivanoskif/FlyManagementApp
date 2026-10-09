from django.db import models
from django.conf import settings

# Create your models here.

class PassengerProfile(models.Model):

    class MembershipLevel(models.TextChoices):
        BASIC = "BASIC", "Basic"
        PLUS = "PLUS", "Plus"
        PREMIUM = "PREMIUM", "Premium"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="passenger_profile",
    )
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    phone = models.CharField(max_length=30, blank=True, null=True)

    date_of_birth = models.DateField(blank=True, null=True)
    nationality = models.CharField(max_length=80, blank=True, null=True)
    document_no = models.CharField(max_length=50, blank=True, null=True)

    membership_level = models.CharField(
        max_length=10,
        choices=MembershipLevel.choices,
        default=MembershipLevel.BASIC,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.user.username})"

    @property
    def can_choose_seat(self) -> bool:
        return self.membership_level in {self.MembershipLevel.PLUS, self.MembershipLevel.PREMIUM}

    @property
    def can_choose_extra_legroom(self) -> bool:
        return self.membership_level == self.MembershipLevel.PREMIUM
