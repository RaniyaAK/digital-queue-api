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
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Queue
from .serializers import QueueSerializer

# Create Queue
@api_view(['GET', 'POST'])
def create_queue(request):
    if request.method == 'GET':
        return Response({
            "message": "Send the following fields using POST to create a queue.",
            "required_fields": {
                "name": "string (Queue Name)",
                "avg_handle_time": "optional integer (Average handling time in minutes, default=5)"
            }
        })

    if request.method == 'POST':
        name = request.data.get("name")
        avg_handle_time = int(request.data.get("avg_handle_time", 5))

        if not name:
            return Response({"error": "Queue name is required"}, status=400)

        queue = Queue.objects.create(name=name, avg_handle_time=avg_handle_time)

        # Format avg_handle_time as minutes
        queue_data = QueueSerializer(queue).data
        queue_data['avg_handle_time'] = f"{queue.avg_handle_time} mins"

        return Response({"message": "Queue created", "queue": queue_data}, status=201)
    

# Create Counter
@api_view(['GET', 'POST'])
def create_counter(request):
    if request.method == 'GET':
        return Response({
            "message": "Send the following fields using POST to create a counter.",
            "required_fields": {
                "name": "string",
                "queue_id": "integer (Queue ID)"
            }
        })

    if request.method == 'POST':
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
    
    
@api_view(['GET', 'POST'])
def join_queue(request):
    if request.method == 'GET':
        return Response({
            "message": "Send the following fields using POST to join the queue.",
            "required_fields": {
                "user_name": "string",
                "phone_number": "string",
                "queue": "integer (Queue ID)",
                "priority": "optional (1=normal, 2=high, 3=emergency)"
            }
        })

    if request.method == 'POST':
        queue_id = request.data.get("queue")
        user_name = request.data.get("user_name")
        phone_number = request.data.get("phone_number")
        priority = int(request.data.get("priority", 1))

        # --- Validate required fields ---
        if not queue_id or not user_name or not phone_number:
            return Response({"error": "queue, user_name and phone_number are required"}, status=400)

        # --- Get queue ---
        try:
            queue = Queue.objects.get(id=queue_id)
        except Queue.DoesNotExist:
            return Response({"error": "Queue not found"}, status=404)

        # --- Generate next token number ---
        last_token = Token.objects.filter(queue=queue).order_by('-token_number').first()
        next_number = last_token.token_number + 1 if last_token else 1

        # --- Create token ---
        token = Token.objects.create(
            queue=queue,
            token_number=next_number,
            user_name=user_name,
            phone_number=phone_number,
            priority=priority
        )

        # --- Calculate estimated wait time ---
        people_ahead = Token.objects.filter(
            queue=queue,
            status="WAITING",
            token_number__lt=token.token_number
        ).count()
        estimated_wait_time = people_ahead * queue.avg_handle_time
        estimated_wait_time_str = f"{estimated_wait_time} mins" if estimated_wait_time > 1 else "1 min"

        # --- Prepare response ---
        data = TokenSerializer(token).data
        data['estimated_wait_time'] = estimated_wait_time_str
        data.pop('called_at', None)  # Remove called_at
        data.pop('status', None)     # Remove status
        data.pop('counter', None)    # Remove counter

        return Response({
            "message": "Token created successfully",
            "token": data
        }, status=201)


@api_view(['GET', 'POST'])
def call_next(request):
    if request.method == 'GET':
        return Response({
            "message": "Send the following JSON using POST to call the next token.",
            "example_json": {
                "queue_id": 1
            }
        })

    # --- Existing POST logic ---
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

# Complete Token (using queue_id instead of token_id)
@api_view(['POST'])
def complete_token(request, queue_id):
    # Find the token currently being served in this queue
    token = Token.objects.filter(queue_id=queue_id, status="SERVING").first()

    if not token:
        return Response({"error": "No SERVING token found in this queue"}, status=404)

    counter = token.counter

    token.status = "COMPLETED"
    token.save()

    if counter:
        counter.is_busy = False
        counter.save()

    return Response({"message": "Token completed", "token_id": token.id})


@api_view(['GET'])
def current_serving(request, queue_id):
    serving_tokens = Token.objects.filter(queue_id=queue_id, status="SERVING")
    serializer = TokenSerializer(serving_tokens, many=True)
    data = serializer.data

    # Remove 'queue' and 'status' from each token
    for token in data:
        token.pop('queue', None)
        token.pop('status', None)

    return Response(data)


@api_view(['GET'])
def my_token_status(request, token_id):
    try:
        token = Token.objects.get(id=token_id)
    except Token.DoesNotExist:
        return Response({"error": "Token not found"}, status=404)

    # --- Base response ---
    response = {
        "id": token.id,
        "token_number": token.token_number,
        "created_at": token.created_at,
        "user_name": token.user_name,
        "phone_number": token.phone_number,
        "queue": token.queue.id,
        "priority": token.priority,
        "status": token.status,
        "avg_handle_time": f"{token.queue.avg_handle_time} mins"
    }

    # --- Only show wait info if token is WAITING ---
    if token.status == "WAITING":
        people_ahead = Token.objects.filter(
            queue=token.queue,
            status="WAITING",
            token_number__lt=token.token_number
        ).count()

        people_behind = Token.objects.filter(
            queue=token.queue,
            status="WAITING",
            token_number__gt=token.token_number
        ).count()

        total_minutes = people_ahead * token.queue.avg_handle_time
        if total_minutes == 0:
            estimated_wait_time = "0 mins"
        elif total_minutes == 1:
            estimated_wait_time = "1 min"
        else:
            estimated_wait_time = f"{total_minutes} mins"

        response.update({
            "people_ahead": people_ahead,
            "people_behind": people_behind,
            "estimated_wait_time": estimated_wait_time
        })
    else:
        # Show called_at only if token is SERVING or COMPLETED
        response["called_at"] = token.called_at

    return Response(response)

@api_view(['GET'])
def list_queues(request):
    queues = Queue.objects.all()
    serializer = QueueSerializer(queues, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def list_counters(request):
    counters = Counter.objects.all()
    serializer = CounterSerializer(counters, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def list_tokens(request):
    tokens = Token.objects.all()
    serializer = TokenSerializer(tokens, many=True)
    return Response(serializer.data)
