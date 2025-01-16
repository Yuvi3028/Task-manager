from django import forms
from .models import Task, Category
from django.contrib.auth.models import User


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter category name'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise forms.ValidationError('This field cannot be empty.')
        return name

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['task_name', 'category', 'assigned_to', 'start_date', 'end_date']

    task_name = forms.CharField(max_length=255)
    category = forms.CharField(max_length=255)
    assigned_to = forms.CharField(max_length=255)
    start_date = forms.DateField()
    end_date = forms.DateField()

    def __init__(self, *args, **kwargs):
        # Dynamically set task_name choices from a list provided during view initialization
        tasks = kwargs.pop('tasks', [])
        super(TaskForm, self).__init__(*args, **kwargs)
        self.fields['task_name'].choices = [(task, task) for task in tasks]
    # Priority field
    # priority = forms.IntegerField(min_value=1, initial=1, required=True)

    # Description
    # description = forms.CharField(
    #     widget=forms.Textarea(attrs={"rows": 3}),
    #     required=False
    # )

    # Organizer
    # organizer = forms.CharField(
    #     max_length=100,
    #     required=True,
    #     widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter organizer"})
    # )
    


