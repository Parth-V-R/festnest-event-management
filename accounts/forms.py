from django import forms

from .models import Profile


class ProfileForm(forms.ModelForm):
    username = forms.CharField(required=True)
    email = forms.EmailField(required=False, label='Email ID')

    class Meta:
        model = Profile
        fields = [
            'username',
            'full_name',
            'email',
            'college',
            'department',
            'year_of_study',
            'section',
            'roll_no',
            'phone',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Enter full name'}),
            'college': forms.TextInput(attrs={'placeholder': 'Enter college name'}),
            'department': forms.TextInput(attrs={'placeholder': 'Enter department'}),
            'year_of_study': forms.TextInput(attrs={'placeholder': 'e.g., 1st Year'}),
            'section': forms.TextInput(attrs={'placeholder': 'e.g., A'}),
            'roll_no': forms.TextInput(attrs={'placeholder': 'e.g., 23CS101'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Enter phone number'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.original_phone = self.instance.phone or '' if self.instance and self.instance.pk else ''
        if user and not self.is_bound:
            self.fields['username'].initial = user.username
            self.fields['email'].initial = user.email

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if not username:
            raise forms.ValidationError('Username is required.')
        if self.user and self.user.username == username:
            return username
        if self.user and self.user.__class__.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile_user = self.user
        if self.user is not None:
            new_username = self.cleaned_data.get('username', '').strip()
            new_email = self.cleaned_data.get('email', '').strip()
            username_changed = profile_user.username != new_username
            email_changed = profile_user.email != new_email
            new_phone = self.cleaned_data.get('phone', '').strip()
            profile.phone = new_phone

            profile_user.username = new_username
            profile_user.email = new_email
            if email_changed:
                profile.email_verified = False
            if self.original_phone != new_phone:
                profile.phone_verified = False
            if not new_phone:
                profile.phone_verified = False
            if commit:
                update_fields = []
                if username_changed:
                    update_fields.append('username')
                if email_changed:
                    update_fields.append('email')
                if update_fields:
                    profile_user.save(update_fields=update_fields)
        if commit:
            profile.save()
        return profile
