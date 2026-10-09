from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from accounts.models import PassengerProfile

User = get_user_model()


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"class": "form-control"}))
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={"class": "form-control"}))

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control"})
        self.fields["password1"].widget.attrs.update({"class": "form-control"})
        self.fields["password2"].widget.attrs.update({"class": "form-control"})


class ProfileForm(forms.ModelForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"class": "form-control"}))
    user_first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={"class": "form-control"}))
    user_last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={"class": "form-control"}))

    class Meta:
        model = PassengerProfile
        fields = ["phone", "date_of_birth", "nationality", "document_no"]
        widgets = {
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "date_of_birth": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "nationality": forms.TextInput(attrs={"class": "form-control"}),
            "document_no": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user

        if user:
            self.fields["email"].initial = user.email
            self.fields["user_first_name"].initial = user.first_name
            self.fields["user_last_name"].initial = user.last_name

    def save(self, commit=True):
        profile = super().save(commit=False)

        if "user_first_name" in self.cleaned_data:
            profile.first_name = self.cleaned_data["user_first_name"]
        if "user_last_name" in self.cleaned_data:
            profile.last_name = self.cleaned_data["user_last_name"]

        if commit:
            profile.save()

            if self._user:
                self._user.email = self.cleaned_data["email"]
                self._user.first_name = self.cleaned_data["user_first_name"]
                self._user.last_name = self.cleaned_data["user_last_name"]
                self._user.save(update_fields=["email", "first_name", "last_name"])

        return profile


class DemoPaymentForm(forms.Form):
    card_number = forms.CharField(
        max_length=19,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "4111 1111 1111 1111"})
    )
    expiry = forms.CharField(
        max_length=7,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "MM/YY"})
    )
    cvv = forms.CharField(
        max_length=4,
        required=True,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "123"})
    )
    name_on_card = forms.CharField(
        max_length=80,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Name Surname"})
    )