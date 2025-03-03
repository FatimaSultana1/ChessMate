from django import forms
from django.contrib.auth.models import User
import chess
from .models import JournalEntry  

class ChessMoveForm(forms.Form):
    uci_move = forms.CharField(label='Move', max_length=5)

    def __init__(self, *args, **kwargs):
        self.board = kwargs.pop('board', chess.Board())
        super(ChessMoveForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(ChessMoveForm, self).clean()
        uci_move = cleaned_data.get('uci_move')

        try:
            move = chess.Move.from_uci(uci_move)
            if move not in self.board.legal_moves:
                raise forms.ValidationError("This move is not allowed.")
        except ValueError:
            raise forms.ValidationError("Invalid move format. Use UCI notation like 'e2e4'.")

        cleaned_data['move'] = move
        return cleaned_data

class JoinForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    email = forms.CharField(widget=forms.TextInput(attrs={'size': '30'}))
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password')
        help_texts = {
            'username': None
        }

    def save(self, commit=True):
        user = super(JoinForm, self).save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput())

class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['entry']
