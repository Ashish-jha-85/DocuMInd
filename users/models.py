from django.db import models
from django.contrib.auth.models import AbstractUser


# Extendable User model
class User(AbstractUser):
    ROLE_CHOICES = [
        ("HR", "HR"),
        ("Finance", "Finance"),
        ("Legal", "Legal"),
        ("Contracts", "Contracts"),
        ("Tech", "Technical Reports"),
    ]
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default="HR")
