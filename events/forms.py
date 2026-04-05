from django import forms

from .models import Event


class EventForm(forms.ModelForm):
    capacity_limited = forms.BooleanField(
        required=False,
        label='Limit capacity',
        help_text='Turn ON to set capacity and optionally enable waitlist.',
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Event description'}),
    )
    capacity = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={'min': 1}),
    )
    min_team_size = forms.IntegerField(
        required=False,
        min_value=2,
        widget=forms.NumberInput(attrs={'min': 2}),
    )
    max_team_size = forms.IntegerField(
        required=False,
        min_value=2,
        widget=forms.NumberInput(attrs={'min': 2}),
    )

    class Meta:
        model = Event
        fields = [
            'title',
            'category',
            'date',
            'description',
            'capacity_limited',
            'capacity',
            'waitlist_enabled',
            'is_team_event',
            'min_team_size',
            'max_team_size',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Event title'}),
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].choices = [('', ' ')] + list(Event.CATEGORY_CHOICES)
        self.fields['capacity_limited'].initial = (
            self.instance.capacity_limited if self.instance and self.instance.pk else False
        )

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('capacity_limited'):
            cleaned_data['waitlist_enabled'] = False
            cleaned_data['capacity'] = cleaned_data.get('capacity') or 100
        else:
            capacity = cleaned_data.get('capacity')
            if capacity is None:
                self.add_error('capacity', 'Capacity is required when limit capacity is ON.')
        if not cleaned_data.get('is_team_event'):
            cleaned_data['min_team_size'] = 2
            cleaned_data['max_team_size'] = 4
        else:
            min_size = cleaned_data.get('min_team_size')
            max_size = cleaned_data.get('max_team_size')
            if min_size is None:
                self.add_error('min_team_size', 'Min team size is required when team event is ON.')
            if max_size is None:
                self.add_error('max_team_size', 'Max team size is required when team event is ON.')
            if min_size is not None and max_size is not None and min_size > max_size:
                self.add_error('max_team_size', 'Max team size must be greater than or equal to min team size.')
        return cleaned_data
