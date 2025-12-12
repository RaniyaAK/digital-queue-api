from django.urls import path
from .views import (
    create_queue, create_counter,
    join_queue, 
    call_next, skip_token, complete_token,
    current_serving,
    my_token_status,
    list_counters,list_queues,list_tokens
)

urlpatterns = [
    path("create-queue/", create_queue),
    path("create-counter/", create_counter),
    path("join/", join_queue),
    path("next/", call_next),
    path("skip/<int:token_id>/", skip_token),
    path('complete/<int:queue_id>/', complete_token),
    path("serving/<int:queue_id>/", current_serving),
    path("my-token/<int:token_id>/", my_token_status),
    path("queues/", list_queues),
    path("counters/", list_counters),
    path("tokens/", list_tokens),

]

#  {
#         "user_name": "string",
#         "phone_number": "string",
#         "queue": 1
#     }
