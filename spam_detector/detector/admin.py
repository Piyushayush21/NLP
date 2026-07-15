from django.contrib import admin
from .models import PredictionHistory


@admin.register(PredictionHistory)
class PredictionHistoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'label', 'confidence', 'text_preview', 'source', 'created_at']
    list_filter = ['label', 'source', 'created_at']
    search_fields = ['text']
    readonly_fields = ['created_at', 'spam_probability', 'ham_probability', 'text_length']
    ordering = ['-created_at']

    def text_preview(self, obj):
        return obj.text[:80] + '...' if len(obj.text) > 80 else obj.text
    text_preview.short_description = 'Text Preview'
