# signals.py

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


@receiver(user_logged_in)
def on_user_logged_in(sender, user, request, **kwargs):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'presence',
        {
            'type': 'user_online',
            'user_id': user.id,
            'username': user.username,
        }
    )


@receiver(user_logged_out)
def on_user_logged_out(sender, user, request, **kwargs):
    if user is None:
        # Handle cases where user is already None
        return
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'presence',
        {
            'type': 'user_offline',
            'user_id': user.id,
            'username': user.username,
        }
    )



# # signals.py
# from django.contrib.auth.signals import user_logged_in, user_logged_out
# from django.dispatch import receiver
# from channels.layers import get_channel_layer
# from asgiref.sync import async_to_sync

# @receiver(user_logged_in)
# def on_user_logged_in(sender, user, request, **kwargs):
#     channel_layer = get_channel_layer()
#     async_to_sync(channel_layer.group_send)(
#         'new_game_updates',
#         {
#             'type': 'new_game_update',
#             'action': 'update',
#         }
#     )

# @receiver(user_logged_out)
# def on_user_logged_out(sender, user, request, **kwargs):
#     channel_layer = get_channel_layer()
#     async_to_sync(channel_layer.group_send)(
#         'new_game_updates',
#         {
#             'type': 'new_game_update',
#             'action': 'update',
#         }
#     )
