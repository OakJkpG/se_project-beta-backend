from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import random

# Don't automatically create profiles - let serializers handle this
# since they need specific profile types and verification codes
class Profile(models.Model):
    USER_TYPE_CHOICES = (
        ('reader', 'Reader'),
        ('publisher', 'Publisher'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    id_card = models.CharField(max_length=50, blank=True, null=True)
    verification_code = models.CharField(max_length=6, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} Profile"
    
    @staticmethod
    def generate_verification_code():
        """Generate a random 6-digit verification code"""
        return str(random.randint(100000, 999999))
