from django import forms

from .models import Event


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'category', 'date', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Event title'}),
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(
                attrs={'rows': 4, 'placeholder': 'Event description'},
            ),
        }
