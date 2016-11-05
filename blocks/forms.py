from django import forms


class SearchForm(forms.Form):
    search = forms.CharField(max_length=255)
