from django.db import models
from users.models import User


class Document(models.Model):
    CATEGORY_CHOICES = [
        ("Finance", "Finance"),
        ("HR", "HR"),
        ("Legal", "Legal"),
        ("Tech", "Technical Reports"),
        ("Unknown", "Unknown"),
    ]
    FILE_TYPE_CHOICES = [
        ("pdf", "PDF"),
        ("docx", "DOCX"),
        ("doc", "DOC"),
        ("txt", "TXT"),
        ("csv", "CSV"),
        ("other", "Other"),
    ]
    title = models.CharField(max_length=255, blank=True, null=True)
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        null=True,
        blank=True,
        default="Unknown",  # default if category not detected
    )
    file_type = models.CharField(
        max_length=10, choices=FILE_TYPE_CHOICES, default="other"
    )
    author = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    uploader = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to="")
    summary = models.TextField(blank=True, null=True)
    entities = models.JSONField(blank=True, null=True)  # store extracted entities
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"Document {self.id}"


class DocumentEmbedding(models.Model):
    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name="embedding"
    )
    vector = models.BinaryField()  # store serialized embedding (pickle/np array)


class AccessLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, null=True, blank=True  # 👈 important
    )
    action = models.CharField(max_length=50)  # e.g. upload, view, login, logout
    timestamp = models.DateTimeField(auto_now_add=True)
