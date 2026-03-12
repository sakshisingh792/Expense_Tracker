# expenses/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# -----------------------------------------------------
# 1. The dynamic Category table
# -----------------------------------------------------
class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)

    class Meta:
        unique_together = ('user', 'name')

    def __str__(self):
        return self.name

# -----------------------------------------------------
# 2. Your Expense Model 
# -----------------------------------------------------
class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    description = models.CharField(max_length=255)
    date = models.DateField(auto_now_add=True)
    receipt = models.ImageField(upload_to='receipts/', null=True, blank=True)

    def __str__(self):
        cat_name = self.category.name if self.category else "Uncategorized"
        return f"{cat_name} - {self.amount} by {self.user.username}"

# -----------------------------------------------------
# 3. Your CategoryBudget Model 
# -----------------------------------------------------
class CategoryBudget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    limit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('user', 'category')

    def __str__(self):
        return f"{self.user.username} - {self.category.name} Budget"

# -----------------------------------------------------
# 4. Your Savings Goals Model
# -----------------------------------------------------
class SavingsGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100) 
    target_amount = models.DecimalField(max_digits=10, decimal_places=2)
    current_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    def progress_percentage(self):
        if self.target_amount > 0:
            percentage = (self.current_amount / self.target_amount) * 100
            return min(percentage, 100)
        return 0    

# -----------------------------------------------------
# 5. Your FULLY MERGED UserProfile Model
# -----------------------------------------------------
CURRENCY_CHOICES = [
    ('$', 'USD ($)'),
    ('₹', 'INR (₹)'),
    ('€', 'EUR (€)'),
    ('£', 'GBP (£)'),
]

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Financial Settings
    monthly_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='₹')
    budget_alert_percentage = models.IntegerField(default=80, help_text="Warn me when I spend this % of my salary")
    
    # New Profile Picture!
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

# -----------------------------------------------------
# 6. SIGNALS: Automatically create profiles
# -----------------------------------------------------
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if not hasattr(instance, 'userprofile'):
        UserProfile.objects.create(user=instance)
    instance.userprofile.save()