import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from .models import Game, Move, Challenge
import chess
from .utils import fen_to_board_dict
import redis
from django.conf import settings

# Initialize Redis connection
redis_conn = redis.Redis(host='localhost', port=6379, db=0)

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.game_group_name = f"game_{self.game_id}"

        # Join game group
        await self.channel_layer.group_add(
            self.game_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave game group
        await self.channel_layer.group_discard(
            self.game_group_name,
            self.channel_name
        )

    @database_sync_to_async
    def handle_resign(self, user_id):
        try:
            user = User.objects.get(id=user_id)
            game = Game.objects.get(id=self.game_id, is_active=True)
        except (User.DoesNotExist, Game.DoesNotExist):
            return {'error': 'Invalid game or user'}

        # Determine the winner (the other player)
        if user == game.player_white:
            game.winner = game.player_black
        elif user == game.player_black:
            game.winner = game.player_white
        else:
            return {'error': 'You are not a player in this game'}

        game.is_active = False
        game.save()
        board_html = render_to_string('chessboard/chessboard.html', {
            'board': fen_to_board_dict(game.fen),
            'files': ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'],
        })

        return {
            'fen': game.fen,
            'is_active': game.is_active,
            'winner': game.winner.username,
            'board_html': board_html,
            'is_white_turn': chess.Board(game.fen).turn == chess.WHITE,
        }


    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')
        user_id = data.get('user_id')  
        if action == 'move':
            move_uci = data.get('move')
            if move_uci and user_id:
                # Validate and apply the move
                result = await self.handle_move(user_id, move_uci)
                if 'error' in result:
                    # Send error message back to the user
                    await self.send(text_data=json.dumps({'error': result['error']}))
                else:
                    # Broadcast the updated game state to all group members
                    await self.channel_layer.group_send(
                        self.game_group_name,
                        {
                            'type': 'game_update',
                            'fen': result['fen'],
                            'is_active': result['is_active'],
                            'winner': result['winner'],
                            'board_html': result['board_html'],
                            'is_white_turn': result['is_white_turn'],
                        }
                    )
        elif action == 'resign':
            result = await self.handle_resign(user_id)
            if 'error' in result:
                await self.send(text_data=json.dumps({'error': result['error']}))
            else:
                # Broadcast the game over to all group members
                await self.channel_layer.group_send(
                    self.game_group_name,
                    {
                        'type': 'game_update',
                        'fen': result['fen'],
                        'is_active': result['is_active'],
                        'winner': result['winner'],
                        'board_html': result['board_html'],
                        'is_white_turn': result['is_white_turn'],
                    }
                )


    async def game_update(self, event):
        fen = event['fen']
        is_active = event['is_active']
        winner = event['winner']
        board_html = event['board_html']
        is_white_turn = event['is_white_turn']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'fen': fen,
            'is_active': is_active,
            'winner': winner,
            'board_html': board_html,
            'is_white_turn': is_white_turn,
        }))

    @database_sync_to_async
    def handle_move(self, user_id, move_uci):
        try:
            user = User.objects.get(id=user_id)
            game = Game.objects.get(id=self.game_id, is_active=True)
        except (User.DoesNotExist, Game.DoesNotExist):
            return {'error': 'Invalid game or user'}

        board = chess.Board(game.fen)

        # Check if it's the user's turn
        if (board.turn == chess.WHITE and user != game.player_white) or \
        (board.turn == chess.BLACK and user != game.player_black):
            return {'error': "It's not your turn"}

        try:
            move = chess.Move.from_uci(move_uci)
        except ValueError:
            return {'error': 'Invalid move format'}  # Invalid move format

        if move not in board.legal_moves:
            return {'error': 'Illegal move'}  # Move not allowed

        board.push(move)
        game.fen = board.fen()
        Move.objects.create(game=game, player=user, uci=move_uci)

        # Render updated board HTML
        board_html = render_to_string('chessboard/chessboard.html', {
            'board': fen_to_board_dict(game.fen),
            'files': ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'],
        })

        # Check for game over
        if board.is_game_over():
            game.is_active = False
            result = board.result()
            if result == '1-0':
                game.winner = game.player_white
            elif result == '0-1':
                game.winner = game.player_black
            else:
                game.winner = None  # Draw
            game.save()
            winner_username = game.winner.username if game.winner else None
        else:
            game.save()
            winner_username = None

        return {
            'fen': game.fen,
            'is_active': game.is_active,
            'winner': winner_username,
            'board_html': board_html,
            'is_white_turn': board.turn == chess.WHITE,
        }


# consumers.py

class NewGameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'new_game_updates'
        user = self.scope['user']

        if user.is_authenticated:
            # Add user to Redis
            await self.add_user_online(user.id)

            # Join group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )

            await self.accept()

            # Notify all clients to update their lobby
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'new_game_update',
                    'action': 'update',
                }
            )
            print(f"User {user.username} connected to new_game_updates group.")
        else:
            await self.close()

    async def disconnect(self, close_code):
        user = self.scope['user']

        if user.is_authenticated:
            # Remove user from Redis
            await self.remove_user_online(user.id)

            # Leave group
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

            # Notify all clients to update their lobby
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'new_game_update',
                    'action': 'update',
                }
            )
            print(f"User {user.username} disconnected from new_game_updates group.")

    @database_sync_to_async
    def add_user_online(self, user_id):
        redis_conn.sadd('online_users', user_id)

    @database_sync_to_async
    def remove_user_online(self, user_id):
        redis_conn.srem('online_users', user_id)

    async def new_game_update(self, event):
        action = event.get('action')
        if action == 'update':
            await self.send(text_data=json.dumps({'action': 'update'}))

class UserConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.user_group_name = f'user_{self.user_id}'

        # Join user group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave user group
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )

    # Receive message from group
    async def user_update(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event))
