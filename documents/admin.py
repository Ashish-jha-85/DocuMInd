from django.contrib import admin
from .models import Document, DocumentEmbedding, AccessLog


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "uploader", "date", "created_at")
    list_filter = ("category", "date", "uploader")
    search_fields = ("title", "author", "summary")


@admin.register(DocumentEmbedding)
class DocumentEmbeddingAdmin(admin.ModelAdmin):
    list_display = ("document",)
    readonly_fields = ("vector",)


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ("user", "document", "action", "timestamp")
    list_filter = ("action", "timestamp", "user")
    search_fields = ("user__username", "document__title")
