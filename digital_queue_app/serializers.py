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
from rest_framework import serializers
from .models import Token, Queue

class TokenSerializer(serializers.ModelSerializer):
    token_number = serializers.IntegerField(read_only=True)  # auto-generated
    queue = serializers.PrimaryKeyRelatedField(queryset=Queue.objects.all())  # accept queue ID

    class Meta:
        model = Token
        fields = [
            'id', 
            'token_number', 
            'user_name', 
            'phone_number', 
            'queue', 
            'priority', 
            'status', 
            'counter', 
            'created_at', 
            'called_at'
        ]
