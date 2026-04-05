from django import forms

from .models import Event


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            'title',
            'category',
            'date',
            'description',
            'capacity',
            'waitlist_enabled',
            'is_team_event',
            'min_team_size',
            'max_team_size',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Event title'}),
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Event description'}),
            'capacity': forms.NumberInput(attrs={'min': 1}),
            'min_team_size': forms.NumberInput(attrs={'min': 2}),
            'max_team_size': forms.NumberInput(attrs={'min': 2}),
        }
