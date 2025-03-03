from django.shortcuts import render, redirect, get_object_or_404
from .models import Game, Move, JournalEntry, Challenge  # Ensure Challenge is imported
from .forms import ChessMoveForm, JoinForm, LoginForm, JournalEntryForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
import chess
from django.contrib import messages
from django.contrib.sessions.models import Session
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.template.loader import render_to_string
from .utils import fen_to_board_dict
from .models import Game, Move
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt

import redis
from django.contrib.auth.models import User

# Initialize Redis connection
redis_conn = redis.Redis(host='localhost', port=6379, db=0)

def get_all_online_users():
    user_ids = redis_conn.smembers('online_users')
    user_ids = [int(uid.decode('utf-8')) for uid in user_ids]
    return User.objects.filter(id__in=user_ids)

@csrf_exempt
@login_required(login_url='login/')
def home(request):
    game = Game.objects.filter(is_active=True, player_white=request.user).first() or \
        Game.objects.filter(is_active=True, player_black=request.user).first() 
    
    if not game:
        # return redirect('new_game')
        pending_challenges = Challenge.objects.filter(opponent=request.user, accepted=False, declined=False)
        sent_challenges = Challenge.objects.filter(challenger=request.user, accepted=False, declined=False)
        active_white_ids = Game.objects.filter(is_active=True).values_list('player_white', flat=True)
        active_black_ids = Game.objects.filter(is_active=True).values_list('player_black', flat=True)
        active_ids = list(active_white_ids) + list(active_black_ids)
        active_users = get_all_online_users().exclude(id=request.user.id).exclude(id__in=active_ids)
        challenged_user_ids = Challenge.objects.filter(challenger=request.user, accepted=False, declined=False).values_list('opponent', flat=True)
        incoming_challenge_user_ids = Challenge.objects.filter(opponent=request.user, accepted=False, declined=False).values_list('challenger', flat=True)
        
        opponents = active_users.exclude(id__in=challenged_user_ids).exclude(id__in=incoming_challenge_user_ids)
        games = Game.objects.filter(player_white=request.user) | Game.objects.filter(player_black=request.user)
        games = games.order_by('-created_at')
        
        game_entries = []
        
        for game in games:
            opponent = game.player_black if game.player_white == request.user else game.player_white
            journal_entry = game.journalentry_set.filter(user=request.user).first()
            if game.winner == request.user:
                outcome = "Win"
            elif game.winner is not None:
                outcome = "Loss"
            else:
                outcome = "Tie"
            game_entries.append({
                'game': game,
                'opponent': opponent,
                'moves_count': game.moves.count(),
                'outcome': outcome,
                'journal_entry': journal_entry,
            })
        context = {
            'pending_challenges': pending_challenges,
            'sent_challenges': sent_challenges,
            'opponents': opponents,
            'game_entries': game_entries,
        }
        return render(request, 'chessboard/new_game.html', context)

    if request.method == 'POST':
        if 'move' in request.POST:
            form = ChessMoveForm(request.POST)
            if form.is_valid():
                move_uci = form.cleaned_data['uci_move']
                user = request.user
                board = chess.Board(game.fen)

                try:
                    move = chess.Move.from_uci(move_uci)
                except ValueError:
                    messages.error(request, "Invalid move format.")
                    return redirect('home')

                if move not in board.legal_moves:
                    messages.error(request, "Illegal move.")
                    return redirect('home')

                board.push(move)
                game.fen = board.fen()
                game.save()
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
                    winner_username = None

                # Send update via channel layer
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'game_{game.id}',
                    {
                        'type': 'game_update',
                        'fen': game.fen,
                        'is_active': game.is_active,
                        'winner': winner_username,
                        'board_html': board_html,
                        'is_white_turn': board.turn == chess.WHITE,
                    }
                )

                if not game.is_active:
                    if winner_username:
                        messages.success(request, f"Game over! {winner_username} wins.")
                    else:
                        messages.success(request, "Game over! It's a draw.")
                    return redirect('home')

                return redirect('home')
        elif 'resign' in request.POST:
            game.is_active = False
            game.winner = game.player_black if game.player_white == request.user else game.player_white
            game.save()

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'game_{game.id}',
                {
                    'type': 'game_update',
                    'fen': game.fen,
                    'is_active': game.is_active,
                    'winner': game.winner.username,
                    'board_html': render_to_string('chessboard/chessboard.html', {
                        'board': fen_to_board_dict(game.fen),
                        'files': ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'],
                    }),
                    'is_white_turn': chess.Board(game.fen).turn == chess.WHITE,
                }
            )

            messages.success(request, f"You have resigned. {game.winner.username} wins.")
            return redirect('home')

    form = ChessMoveForm()
    board = fen_to_board_dict(game.fen)
    context = {
        'game': game,
        'form': form,
        'is_white_turn': chess.Board(game.fen).turn == chess.WHITE,
        'board': board,
        'files': ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'],
    }
    return render(request, 'chessboard/home.html', context)


@csrf_exempt
@login_required
def check_active_game(request):
    game = Game.objects.filter(is_active=True, player_white=request.user).first() or \
           Game.objects.filter(is_active=True, player_black=request.user).first()
    return JsonResponse({'has_active_game': bool(game)})

# views.py (Relevant Sections)

@csrf_exempt
@login_required
def challenge_player(request, opponent_id):
    opponent = get_object_or_404(User, id=opponent_id)
    active_game = Game.objects.filter(is_active=True, player_white=opponent).first() or \
                  Game.objects.filter(is_active=True, player_black=opponent).first()
    if active_game:
        return HttpResponse("Opponent is already in a game.")
    existing_challenge = Challenge.objects.filter(challenger=request.user, opponent=opponent, accepted=False, declined=False).first()
    if existing_challenge:
        return HttpResponse("You have already challenged this player.")
    Challenge.objects.create(challenger=request.user, opponent=opponent)
    # Send WebSocket message to opponent
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'user_{opponent.id}',
        {
            'type': 'user_update',
            'action': 'new_challenge',
            'from': request.user.username,
        }
    )
    return redirect('home')

@csrf_exempt
@login_required
def accept_challenge(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id, opponent=request.user)
    if request.method == 'POST':
        # Create a new game
        game = Game.objects.create(player_white=challenge.challenger, player_black=challenge.opponent)
        challenge.accepted = True
        challenge.save()
        messages.success(request, f"You have accepted the challenge from {challenge.challenger.username}.")
        # Send WebSocket message to challenger
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{challenge.challenger.id}',
            {
                'type': 'user_update',
                'action': 'challenge_accepted',
                'from': request.user.username,
            }
        )
        return redirect('home')
    return render(request, 'chessboard/accept_challenge.html', {'challenge': challenge})

@csrf_exempt
@login_required
def decline_challenge(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id, opponent=request.user)
    if request.method == 'POST':
        challenge.declined = True
        challenge.save()
        messages.info(request, f"You have declined the challenge from {challenge.challenger.username}.")
        # Optionally, notify the challenger
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{challenge.challenger.id}',
            {
                'type': 'user_update',
                'action': 'challenge_declined',
                'from': request.user.username,
            }
        )
        return redirect('home')
    return render(request, 'chessboard/decline_challenge.html', {'challenge': challenge})

@csrf_exempt
def join(request):
    if request.method == 'POST':
        join_form = JoinForm(request.POST)
        if join_form.is_valid():
            user = join_form.save()
            login(request, user)
            return redirect('home')
    else:
        join_form = JoinForm()
    return render(request, 'chessboard/join.html', {'join_form': join_form})


@csrf_exempt
def user_login(request):
    if request.method == 'POST':
        login_form = LoginForm(request.POST)
        if login_form.is_valid():
            username = login_form.cleaned_data['username']
            password = login_form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user:
                if user.is_active:
                    login(request, user)
                    return redirect('home')
                else:
                    return HttpResponse("Your account is not active.")
            else:
                return HttpResponse("Invalid login details supplied.")
    else:
        login_form = LoginForm()
    return render(request, 'chessboard/login.html', {'login_form': login_form})

@csrf_exempt
@login_required
def user_logout(request):
    logout(request)
    return redirect('login')

@csrf_exempt
@login_required
def journal(request):
    games = Game.objects.filter(player_white=request.user) | Game.objects.filter(player_black=request.user)
    games = games.order_by('-created_at')
    game_entries = []
    for game in games:
        opponent = game.player_black if game.player_white == request.user else game.player_white
        try:
            journal_entry = JournalEntry.objects.get(game=game, user=request.user)
        except JournalEntry.DoesNotExist:
            journal_entry = None
        if game.winner == request.user:
            outcome = "Win"
        elif game.winner is not None:
            outcome = "Loss"
        else:
            outcome = "Tie"
        game_entries.append({
            'game': game,
            'opponent': opponent,
            'moves_count': game.moves.count(),
            'outcome': outcome,
            'journal_entry': journal_entry,
        })
    
    context = {
        'game_entries': game_entries,
    }
    return render(request, 'chessboard/journal.html', context)


@csrf_exempt
@login_required
def game_state(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    if game.is_active:
        board_dict = fen_to_board_dict(game.fen)
        html = render_to_string('chessboard/chessboard.html', {
            'board': board_dict,
            'files': ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        })
        is_white_turn = chess.Board(game.fen).turn == chess.WHITE
        return JsonResponse({
            'html': html,
            'is_active': game.is_active,
            'is_white_turn': is_white_turn,
            'winner': None
        })
    else:
        html = ''

    return JsonResponse({'html': html, 'is_active': game.is_active})

@csrf_exempt
@login_required
def add_journal_entry(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    if request.method == 'POST':
        form = JournalEntryForm(request.POST)
        if form.is_valid():
            journal_entry = form.save(commit=False)
            journal_entry.user = request.user
            journal_entry.game = game
            journal_entry.save()
            messages.success(request, "Journal entry added successfully.")
            return redirect('/journal')
    else:
        form = JournalEntryForm()
    return render(request, 'chessboard/add_journal_entry.html', {'form': form, 'game': game})


@csrf_exempt
@login_required
def edit_journal_entry(request, entry_id):
    journal_entry = get_object_or_404(JournalEntry, id=entry_id, user=request.user)
    if request.method == 'POST':
        form = JournalEntryForm(request.POST, instance=journal_entry)
        if form.is_valid():
            form.save()
            messages.success(request, "Journal entry updated successfully.")
            return redirect('/journal')
    else:
        form = JournalEntryForm(instance=journal_entry)
    return render(request, 'chessboard/edit_journal_entry.html', {'form': form, 'journal_entry': journal_entry})


@csrf_exempt
@login_required
def delete_journal_entry(request, entry_id):
    journal_entry = get_object_or_404(JournalEntry, id=entry_id, user=request.user)
    if request.method == 'POST':
        journal_entry.delete()
        messages.success(request, "Journal entry deleted successfully.")
        return redirect('/journal')
    return render(request, 'chessboard/delete_journal_entry.html', {'journal_entry': journal_entry})

@csrf_exempt
def history(request):
    return render(request, 'chessboard/history.html')

@csrf_exempt
def rules(request):
    return render(request, 'chessboard/rules.html')

@csrf_exempt
def about(request):
    return render(request, 'chessboard/about.html')


from django.db.models import Q

@csrf_exempt
@login_required
def fetch_pending_challenges(request):
    pending_challenges = Challenge.objects.filter(opponent=request.user, accepted=False, declined=False)
    challenges_html = render_to_string('chessboard/pending_challenges.html', {'pending_challenges': pending_challenges})
    return JsonResponse({'challenges_html': challenges_html})

@csrf_exempt
@login_required
def fetch_new_game_updates(request):
    # Same context as in the 'home' view when rendering 'new_game.html'
    pending_challenges = Challenge.objects.filter(opponent=request.user, accepted=False, declined=False)
    sent_challenges = Challenge.objects.filter(challenger=request.user, accepted=False, declined=False)
    active_white_ids = Game.objects.filter(is_active=True).values_list('player_white', flat=True)
    active_black_ids = Game.objects.filter(is_active=True).values_list('player_black', flat=True)
    active_ids = list(active_white_ids) + list(active_black_ids)
    
    active_users = get_all_online_users().exclude(id=request.user.id).exclude(id__in=active_ids)
    challenged_user_ids = Challenge.objects.filter(challenger=request.user, accepted=False, declined=False).values_list('opponent', flat=True)
    incoming_challenge_user_ids = Challenge.objects.filter(opponent=request.user, accepted=False, declined=False).values_list('challenger', flat=True)

    opponents = active_users.exclude(id__in=challenged_user_ids).exclude(id__in=incoming_challenge_user_ids)
    games = Game.objects.filter(player_white=request.user) | Game.objects.filter(player_black=request.user)
    games = games.order_by('-created_at')

    # Prepare game entries with user's own journal entries
    game_entries = []
    for game in games:
        opponent = game.player_black if game.player_white == request.user else game.player_white
        journal_entry = game.journalentry_set.filter(user=request.user).first()
        if game.winner == request.user:
            outcome = "Win"
        elif game.winner is not None:
            outcome = "Loss"
        else:
            outcome = "Tie"
        game_entries.append({
            'game': game,
            'opponent': opponent,
            'moves_count': game.moves.count(),
            'outcome': outcome,
            'journal_entry': journal_entry,
        })

    context = {
        'pending_challenges': pending_challenges,
        'sent_challenges': sent_challenges,
        'opponents': opponents,
        'game_entries': game_entries,
    }

    left_html = render_to_string('chessboard/challenge_player_section.html', context, request=request)
    right_html = render_to_string('chessboard/new_game_updates.html', context, request=request)
    return JsonResponse({'left_html': left_html, 'right_html': right_html})


@csrf_exempt
@login_required
def delete_game(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    # Check if the user is one of the players in the game
    if request.user != game.player_white and request.user != game.player_black:
        return HttpResponse("You are not authorized to delete this game.")

    if request.method == 'POST':
        game.delete()
        messages.success(request, "Game and associated entries deleted successfully.")
        return redirect('home')
    else:
        return render(request, 'chessboard/delete_game.html', {'game': game})