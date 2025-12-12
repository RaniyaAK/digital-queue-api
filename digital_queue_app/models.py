from django.db import models
from django.utils import timezone

class Queue(models.Model):
    name = models.CharField(max_length=100)
    avg_handle_time = models.IntegerField(default=5)  # in minutes

    def __str__(self):
        return self.name


class Counter(models.Model):
    name = models.CharField(max_length=50)
    queue = models.ForeignKey(Queue, on_delete=models.CASCADE)
    is_busy = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.queue.name}"


class Token(models.Model):
    STATUS_CHOICES = (
        ('WAITING', 'Waiting'),
        ('SERVING', 'Serving'),
        ('SKIPPED', 'Skipped'),
        ('COMPLETED', 'Completed'),
    )

    queue = models.ForeignKey(Queue, on_delete=models.CASCADE)
    token_number = models.IntegerField()
    priority = models.IntegerField(default=1)  # 1-normal, 2-senior, 3-emergency
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='WAITING')
    counter = models.ForeignKey(Counter, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(default=timezone.now)
    called_at = models.DateTimeField(null=True, blank=True)

    # User info (both required)
    user_name = models.CharField(max_length=100, default="Anonymous")
    phone_number = models.CharField(max_length=15, default="0000000000")

    def __str__(self):
        return f"Token {self.token_number} - {self.user_name} ({self.status})"
