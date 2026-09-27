from django.db import models

# Create your models here.

class Reminder(models.Model):
    title = models.CharField(max_length=255)
    reminder_time = models.DateTimeField()
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["reminder_time"]

    def __str__(self):
        return self.title


class CommandHistory(models.Model):
    command = models.TextField()
    intent = models.CharField(max_length=50)
    response = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.intent}: {self.command[:50]}"