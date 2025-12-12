from rest_framework import serializers
from .models import Queue, Counter, Token

class QueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Queue
        fields = "__all__"

class CounterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Counter
        fields = "__all__"

class TokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Token
        fields = "__all__"
