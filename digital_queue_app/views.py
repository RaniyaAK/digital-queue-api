from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from .models import Queue, Counter, Token
from .serializers import QueueSerializer, CounterSerializer, TokenSerializer
from .serializers import TokenSerializer


# ---------------- Helpers ----------------
def calculate_wait_time(queue, token):
    before_count = Token.objects.filter(
        queue=queue,
        status="WAITING",
        token_number__lt=token.token_number
    ).count()
    return before_count * queue.avg_handle_time

def get_next_token(queue):
    for p in [3,2,1]:  # emergency -> senior -> normal
        token = Token.objects.filter(queue=queue, status="WAITING", priority=p).order_by('token_number').first()
        if token:
            return token
    return None

def assign_to_counter(token):
    counter = Counter.objects.filter(queue=token.queue, is_busy=False).first()
    if not counter:
        return None

    token.status = "SERVING"
    token.counter = counter
    token.called_at = timezone.now()
    token.save()

    counter.is_busy = True
    counter.save()

    return token

# ---------------- API Endpoints ----------------

# Create Queue
@api_view(['POST'])
def create_queue(request):
    name = request.data.get("name")
    avg_handle_time = request.data.get("avg_handle_time", 5)

    if not name:
        return Response({"error": "Queue name is required"}, status=400)

    queue = Queue.objects.create(name=name, avg_handle_time=avg_handle_time)
    return Response({"message": "Queue created", "queue": QueueSerializer(queue).data})

# Create Counter
@api_view(['POST'])
def create_counter(request):
    name = request.data.get("name")
    queue_id = request.data.get("queue_id")

    if not name or not queue_id:
        return Response({"error": "Counter name and queue_id are required"}, status=400)

    try:
        queue = Queue.objects.get(id=queue_id)
    except Queue.DoesNotExist:
        return Response({"error": "Queue not found"}, status=404)

    counter = Counter.objects.create(name=name, queue=queue)
    return Response({"message": "Counter created", "counter": CounterSerializer(counter).data})

# Join Queue
@api_view(['POST'])
def join_queue(request):
    queue_id = request.data.get("queue_id")
    priority = int(request.data.get("priority", 1))
    user_name = request.data.get("user_name")
    phone_number = request.data.get("phone_number")

    if not user_name:
        return Response({"error": "user_name is required"}, status=400)

    try:
        queue = Queue.objects.get(id=queue_id)
    except Queue.DoesNotExist:
        return Response({"error": "Queue not found"}, status=404)

    last_token = Token.objects.filter(queue=queue).order_by('-token_number').first()
    next_number = last_token.token_number + 1 if last_token else 1

    token = Token.objects.create(
        queue=queue,
        token_number=next_number,
        priority=priority,
        user_name=user_name,
        phone_number=phone_number
    )

    wait_time = calculate_wait_time(queue, token)

    return Response({
        "message": "Token generated",
        "token": TokenSerializer(token).data,
        "estimated_wait_time_minutes": wait_time
    })

# Call Next
@api_view(['POST'])
def call_next(request):
    queue_id = request.data.get("queue_id")
    try:
        queue = Queue.objects.get(id=queue_id)
    except Queue.DoesNotExist:
        return Response({"error": "Queue not found"}, status=404)

    token = get_next_token(queue)
    if not token:
        return Response({"message": "No waiting tokens"})

    assigned = assign_to_counter(token)
    if not assigned:
        return Response({"message": "No free counters available"})

    return Response({
        "message": "Next token called",
        "token": TokenSerializer(assigned).data
    })

# Skip Token
@api_view(['POST'])
def skip_token(request, token_id):
    try:
        token = Token.objects.get(id=token_id)
    except Token.DoesNotExist:
        return Response({"error": "Token not found"}, status=404)

    token.status = "SKIPPED"
    token.save()
    return Response({"message": "Token skipped"})

# Complete Token
@api_view(['POST'])
def complete_token(request, token_id):
    try:
        token = Token.objects.get(id=token_id)
    except Token.DoesNotExist:
        return Response({"error": "Token not found"}, status=404)

    counter = token.counter
    token.status = "COMPLETED"
    token.save()

    if counter:
        counter.is_busy = False
        counter.save()

    return Response({"message": "Token completed"})


@api_view(['GET'])
def current_serving(request, queue_id):
    serving_tokens = Token.objects.filter(queue_id=queue_id, status="SERVING")
    serializer = TokenSerializer(serving_tokens, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def my_token_status(request, token_id):
    try:
        token = Token.objects.get(id=token_id)
    except Token.DoesNotExist:
        return Response({"error": "Token not found"}, status=404)

    # --- Count People Ahead ---
    people_ahead = Token.objects.filter(
        queue=token.queue,
        status="WAITING",
        token_number__lt=token.token_number
    ).count()

    # --- Count People Behind ---
    people_behind = Token.objects.filter(
        queue=token.queue,
        status="WAITING",
        token_number__gt=token.token_number
    ).count()

    data = TokenSerializer(token).data
    data["people_ahead"] = people_ahead
    data["people_behind"] = people_behind

    return Response(data)



