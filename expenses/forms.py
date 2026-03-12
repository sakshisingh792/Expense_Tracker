# expenses/forms.py
from django import forms
from .models import Expense, UserProfile,Category
from django.contrib.auth.models import User

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; margin-bottom: 15px;'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; margin-bottom: 15px;'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; margin-bottom: 15px;'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; margin-bottom: 15px;'}),
        }

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        # We only want the user to fill out these three fields.
        # The 'user' and 'date' will be handled automatically by our code!
        fields = ['amount', 'category', 'description','receipt']
        
        # Adding some basic CSS classes so the form doesn't look ugly
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 100%; padding: 8px; margin-bottom: 15px;'}),
            'category': forms.Select(attrs={'class': 'form-control', 'style': 'width: 100%; padding: 8px; margin-bottom: 15px;'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'style': 'width: 100%; padding: 8px; margin-bottom: 15px;'}),
        }

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        # We only want them to edit their salary, nothing else!
        fields = ['monthly_salary','currency', 'budget_alert_percentage']
        
        widgets = {
            'monthly_salary': forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; margin-bottom: 15px;'}),
            'currency': forms.Select(attrs={'class': 'form-control', 'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; margin-bottom: 15px;'}),
            'budget_alert_percentage': forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; margin-bottom: 15px;'}),
        } 

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., Hackathon, Travel, Groceries', 
                'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; margin-bottom: 15px;'
            }),
        }                