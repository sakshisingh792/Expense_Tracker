# expenses/admin.py
from django.contrib import admin
from .models import Expense,UserProfile,CategoryBudget,SavingsGoal

# This tells Django to show our Expense model in the admin panel
admin.site.register(Expense)
admin.site.register(UserProfile)
admin.site.register(CategoryBudget)
admin.site.register(SavingsGoal)

# Register your models here.
