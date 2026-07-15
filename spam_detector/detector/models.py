from django.db import models


class PredictionHistory(models.Model):
    """Stores every spam/ham prediction made via the web UI."""

    LABEL_CHOICES = [
        ('spam', 'Spam'),
        ('ham', 'Ham'),
    ]

    text = models.TextField()
    label = models.CharField(max_length=4, choices=LABEL_CHOICES)
    confidence = models.FloatField(help_text="Confidence percentage (0-100)")
    spam_probability = models.FloatField(default=0.0)
    ham_probability = models.FloatField(default=0.0)
    text_length = models.IntegerField(default=0)
    source = models.CharField(
        max_length=10,
        default='manual',
        choices=[('manual', 'Manual Input'), ('batch', 'Batch Upload')],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Prediction'
        verbose_name_plural = 'Predictions'

    def __str__(self):
        preview = self.text[:60] + '...' if len(self.text) > 60 else self.text
        return f"[{self.label.upper()}] {preview}"

    def text_preview(self):
        return self.text[:120] + '...' if len(self.text) > 120 else self.text
