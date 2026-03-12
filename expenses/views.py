# expenses/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime
from django.db.models import Sum ,Q# NEW: For calculating chart totals
import json # NEW: For passing data to the chart
from .models import Expense,UserProfile,CategoryBudget,Category,SavingsGoal
from .forms import ExpenseForm , UserProfileForm, UserUpdateForm,CategoryForm
import csv
from django.http import HttpResponse#
from decimal import Decimal
from django.template.loader import get_template
from xhtml2pdf import pisa
from datetime import timedelta

import pytesseract
from PIL import Image
import re
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import calendar
# 1. The Landing Page (Admin vs User choice)
# expenses/views.py

@login_required(login_url='login')
def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="my_expenses.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Category', 'Description', 'Amount'])

    # 1. Grab the timeframe choice (default to 'month' if none provided)
    timeframe = request.GET.get('timeframe', 'month')
    search_query = request.GET.get('q', '')
    today = timezone.now().date()
    
    # 2. Start with all expenses, perfectly sorted
    expenses = Expense.objects.filter(user=request.user).order_by('-date', '-id')

    # 3. Filter by Timeframe
    if timeframe == 'day':
        expenses = expenses.filter(date=today)
    elif timeframe == 'month':
        expenses = expenses.filter(date__year=today.year, date__month=today.month)
    elif timeframe == 'year':
        expenses = expenses.filter(date__year=today.year)

    # 4. Filter by Search Bar (so they can export specific searches!)
    if search_query:
        expenses = expenses.filter(
            Q(description__icontains=search_query) | 
            Q(category__name__icontains=search_query)
        )

    # 5. Write data to CSV
    for expense in expenses:
        # Safely grab the category name
        cat_name = expense.category.name if expense.category else "Uncategorized"
        writer.writerow([expense.date, cat_name, expense.description, expense.amount])

    return response

def landing_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'expenses/landing.html')

# 2. Registration View
def register_user(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Automatically log them in after registering
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'expenses/register.html', {'form': form})

# 3. Login View
def login_user(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'expenses/login.html', {'form': form})

# 4. Logout View
def logout_user(request):
    if request.method == 'POST':
        logout(request)
        return redirect('landing')

@login_required(login_url='login')
def dashboard(request):
    # 1. Get ALL expenses for the user
    expenses = Expense.objects.filter(user=request.user).order_by('-date',"-id")
    
    # ---------------------------------------------------------
    # SAVINGS & TIME LOGIC
    # ---------------------------------------------------------
    today = timezone.now().date()
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    monthly_salary = profile.monthly_salary
    currency = profile.currency
    budget_percentage = profile.budget_alert_percentage 
    budget_limit = (monthly_salary * budget_percentage) / 100

    this_month_expenses = expenses.filter(
        date__year=today.year, 
        date__month=today.month
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal(0.00)
    
    this_month_savings = monthly_salary - this_month_expenses

    this_year_expenses = expenses.filter(
        date__year=today.year
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal(0.00)

    user_join_date = request.user.date_joined.date()
    
    if user_join_date.year == today.year:
        months_active = today.month - user_join_date.month + 1
    else:
        months_active = today.month
    
    ytd_salary = monthly_salary * months_active
    this_year_savings = ytd_salary - this_year_expenses
    
    # ---------------------------------------------------------
    # 3. Search Bar Logic
    # ---------------------------------------------------------
    search_query = request.GET.get('q', '')
    if search_query:
        expenses = expenses.filter(
            Q(description__icontains=search_query) | 
            Q(category__name__icontains=search_query) # UPDATED: Search by category name!
        )
    
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal(0.00)
    
    # ---------------------------------------------------------
    # 4. Chart & Category Budget Logic (RELATIONAL DB FIX)
    # ---------------------------------------------------------
    # CHANGED: We now use category__name to get the actual text word
    raw_category_data = list(expenses.order_by('category__name').values('category__name').annotate(total=Sum('amount')))
    
    user_budgets = CategoryBudget.objects.filter(user=request.user)
    # CHANGED: Use b.category.name to build the dictionary
    budget_dict = {b.category.name: b.limit for b in user_budgets}
    
    labels = []
    totals = []
    category_data = [] 
    
    for item in raw_category_data:
        # CHANGED: Get the name, or default to "Uncategorized" if it's blank
        cat_name = item['category__name'] or "Uncategorized"
        spent = item['total']
        
        labels.append(cat_name)
        totals.append(float(spent))
        
        limit = budget_dict.get(cat_name, Decimal('0.00'))
        
        percent = 0
        warning = False
        if limit > 0:
            percent = min((spent / limit) * 100, 100) 
            warning = percent >= 80 
            
        category_data.append({
            'category': cat_name,
            'total': spent,
            'limit': limit,
            'percent': percent,
            'warning': warning
        })
    # ---------------------------------------------------------
   
    # 5. Pack ALL the new math into the context dictionary
    goals = SavingsGoal.objects.filter(user=request.user)
    # ==========================================
    # NEW: 6-MONTH TREND LINE CHART LOGIC
    # ==========================================
    today = timezone.now().date()
    
    # 1. Setup a blank dictionary for the last 6 months (e.g., {'Oct': 0, 'Nov': 0})
    trend_data = {}
    for i in range(5, -1, -1):
        month_index = (today.month - i - 1) % 12 + 1
        month_name = calendar.month_abbr[month_index]
        trend_data[month_name] = 0

    # 2. Get all expenses from exactly 180 days ago to today
    six_months_ago = today - timedelta(days=180)
    recent_trend_expenses = Expense.objects.filter(user=request.user, date__gte=six_months_ago)

    # 3. Add the amounts into the correct month bucket!
    for exp in recent_trend_expenses:
        month_name = calendar.month_abbr[exp.date.month]
        if month_name in trend_data:
            trend_data[month_name] += float(exp.amount)

    # 4. Convert the dictionary to lists for the JavaScript chart
    line_labels = list(trend_data.keys())
    line_data = list(trend_data.values())
    total_transaction_count = expenses.count()
    if not search_query:
        expenses = expenses[:10]

    # ==========================================
    # NEW USP: SMART AI FINANCIAL INSIGHTS
    # ==========================================
    insight_message = "Keep logging expenses to unlock personalized AI financial insights!"
    
    if total_expenses > 0 and category_data:
        biggest_drain = max(category_data, key=lambda x: x['total'])
        drain_name = biggest_drain['category']
        drain_amount = biggest_drain['total']
        potential_savings = float(drain_amount) * 0.15
        
        if this_month_expenses >= budget_limit and budget_limit > 0:
            insight_message = f"🚨 Alert: You've exceeded your monthly budget. Pause non-essential spending in '{drain_name}' to recover!"
        else:
            insight_message = f"💡 Smart Insight: Your biggest expense is {drain_name} ({currency}{drain_amount}). Cutting this by just 15% would save you an extra {currency}{potential_savings:.2f} this month!"

    # Don't forget to add 'insight_message': insight_message, inside your context dictionary!    
    context = {
        'expenses': expenses,
        'labels': json.dumps(labels),
        'totals': json.dumps(totals),
        'total_expenses': total_expenses,
        'search_query': search_query,
        'monthly_salary': monthly_salary,
        'this_month_savings': this_month_savings,
        'this_year_savings': this_year_savings,
        'currency': currency, 
        'budget_limit': budget_limit, 
        'this_month_expenses': this_month_expenses,
        'budget_percentage': budget_percentage,
        'category_data': category_data,
        'goals': goals,
        'line_labels': line_labels, # <-- ADD THIS
        'line_data': line_data,
        'total_transaction_count': total_transaction_count,
        'insight_message': insight_message,
    }
   
    
    # 2. Add 'goals' to your context dictionary
    


    return render(request, 'expenses/dashboard.html', context)

@login_required(login_url='login')
def add_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST,request.FILES)
        form.fields['category'].queryset = Category.objects.filter(user=request.user)
        if form.is_valid():
            # commit=False means "wait, don't save to the database yet!"
            expense = form.save(commit=False)
            # We must manually attach the logged-in user to this expense
            expense.user = request.user
            # Now we can safely save it
            expense.save()
            return redirect('dashboard') # Send them back to the dashboard
    else:
        form = ExpenseForm() # Show a blank form
        form.fields['category'].queryset = Category.objects.filter(user=request.user)
    
    return render(request, 'expenses/add_expense.html', {'form': form})


@login_required(login_url='login')
def edit_expense(request, id):
    # Fetch the specific expense. Notice we check user=request.user!
    # This acts as a firewall so a user can't edit someone else's expense by guessing an ID.
    expense = get_object_or_404(Expense, id=id, user=request.user)
    
    if request.method == 'POST':
        # instance=expense tells the form to OVERWRITE the existing data, not create a new row
        form = ExpenseForm(request.POST, instance=expense)
        
        form.fields['category'].queryset = Category.objects.filter(user=request.user)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        # Pre-fill the form with the existing expense data
        form = ExpenseForm(instance=expense)

        form.fields['category'].queryset = Category.objects.filter(user=request.user)
        
    return render(request, 'expenses/edit_expense.html', {'form': form})

# NEW: Delete View
@login_required(login_url='login')
def delete_expense(request, id): # Note: your ID variable might be called expense_id instead of pk!
    # 1. Find the expense
    expense = get_object_or_404(Expense, id=id, user=request.user)
    
    # 2. THE FIX: Check if this expense was a Savings Goal deposit!
    # (If your category is just a string, use expense.category == "💰 Savings Goals")
    category_name = str(expense.category) 
    
    if "Savings Goals" in category_name:
        # Extract the exact goal name (e.g., changes "Funded Goal: Ujjain Trip" to "Ujjain Trip")
        goal_name = expense.description.replace("Funded Goal: ", "")
        
        try:
            # Find the goal and subtract the money back out!
            goal = SavingsGoal.objects.get(user=request.user, name=goal_name)
            goal.current_amount -= expense.amount
            
            # Prevent the bar from dropping below 0
            if goal.current_amount < 0: 
                goal.current_amount = 0
                
            goal.save()
        except SavingsGoal.DoesNotExist:
            pass # If the goal doesn't exist anymore, just ignore and proceed
            
    # 3. Delete the expense from the table
    expense.delete()
    return redirect('dashboard')

@login_required(login_url='login')
def settings(request):
    # 1. Fetch the user's specific profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # 2. Ensure a budget backpack exists for every single category
    categories = Category.objects.filter(user=request.user)
    for cat in categories:
        CategoryBudget.objects.get_or_create(user=request.user, category=cat)
    
    # 3. Grab the list of budgets to send to the Settings page
    budgets = CategoryBudget.objects.filter(user=request.user).order_by('category__name')
    
    # 4. Handle the General Settings Form
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('settings') # Stay on the settings page after saving
    else:
        form = UserProfileForm(instance=profile)
        
    return render(request, 'expenses/settings.html', {
        'form': form,
        'budgets': budgets,
        'profile': profile
    })
# expenses/views.py

@login_required(login_url='login')
def history(request):
    # 1. Get the current date in your local timezone
    today = timezone.now().date()
    
    # 2. Check the URL for the user's chosen timeframe (default to 'month' if none is selected)
    timeframe = request.GET.get('timeframe', 'month')
    specific_date = request.GET.get('specific_date', '')
    # 3. Start with ALL expenses
    expenses = Expense.objects.filter(user=request.user).order_by('-date',"-id")
    
    # 4. Filter the database based on the chosen timeframe
    if specific_date:
        try:
            # Force the raw string 'YYYY-MM-DD' into a real Python Date object
            parsed_date = datetime.strptime(specific_date, '%Y-%m-%d').date()
            
            # Now filter the database using the perfect Python object
            expenses = expenses.filter(date=parsed_date)
            
            # Make the title look pretty (e.g., "History for Mar 15, 2026")
            title = f"History for {parsed_date.strftime('%b %d, %Y')}"
            timeframe = 'custom' 
        except ValueError:
            # If the browser sends a corrupted date format, ignore it and default to 'month'
            pass
    elif timeframe == 'day':
        expenses = expenses.filter(date=today)
        title = "Today's History"
    elif timeframe == 'year':
        expenses = expenses.filter(date__year=today.year)
        title = "This Year's History"
    else: # Default to 'month'
        expenses = expenses.filter(date__year=today.year, date__month=today.month)
        title = "This Month's History"
        
    # 5. Calculate Chart Data for this specific timeframe
    category_data = expenses.order_by('category').values('category').annotate(total=Sum('amount'))
    labels = [item['category'] for item in category_data]
    totals = [float(item['total']) for item in category_data]
    
    # 6. Safely get the user's currency
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    context = {
        'expenses': expenses,
        'labels': json.dumps(labels),
        'totals': json.dumps(totals),
        'timeframe': timeframe,
        'title': title,
        'currency': profile.currency,
        'specific_date': specific_date,
    }
    return render(request, 'expenses/history.html', context)




@login_required(login_url='login')
def export_pdf(request):
    timeframe = request.GET.get('timeframe', 'month')
    search_query = request.GET.get('q', '')
    today = timezone.now().date()
    expenses = Expense.objects.filter(user=request.user).order_by('-date', '-id')

    # 1. Filter by Timeframe & Generate a dynamic Title for the PDF
    if timeframe == 'day':
        expenses = expenses.filter(date=today)
        report_title = f"Daily Report ({today.strftime('%b %d, %Y')})"
    elif timeframe == 'year':
        expenses = expenses.filter(date__year=today.year)
        report_title = f"Yearly Report ({today.year})"
    elif timeframe == 'all':
        report_title = "All-Time Expense Report"
    else: # Default to month
        expenses = expenses.filter(date__year=today.year, date__month=today.month)
        report_title = f"Monthly Report ({today.strftime('%B %Y')})"

    # 2. Filter by Search Bar
    if search_query:
        expenses = expenses.filter(
            Q(description__icontains=search_query) | 
            Q(category__name__icontains=search_query)
        )
        report_title += f" (Search: {search_query})"

    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    # 3. We pass the dynamic report_title into the 'month' variable so your existing HTML template doesn't break!
    context = {
        'expenses': expenses,
        'total': total_expenses,
        'user': request.user,
        'month': report_title, 
        'currency': profile.currency,
    }

    # Clean up the title so it's safe to use as a computer filename
    safe_filename = report_title.replace(' ', '_').replace(',', '').replace('(', '').replace(')', '').replace(':', '')
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Expense_Report_{safe_filename}.pdf"'

    template = get_template('expenses/pdf_report.html')
    html = template.render(context)
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse(f'We had some errors <pre>{html}</pre>')
        
    return response


@login_required(login_url='login')
def manage_categories(request):
    # Fetch all categories that belong strictly to the logged-in user
    categories = Category.objects.filter(user=request.user)

    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            # Pause the save to attach the logged-in user
            new_category = form.save(commit=False)
            new_category.user = request.user
            new_category.save()
            return redirect('manage_categories') # Refresh the page
    else:
        form = CategoryForm()

    context = {
        'form': form,
        'categories': categories,
    }
    return render(request, 'expenses/manage_categories.html', context)

from django.shortcuts import redirect
# Make sure you have SavingsGoal imported at the top of your file!

def add_goal(request):
    if request.method == 'POST':
        # 1. Grab the data from the HTML form
        goal_name = request.POST.get('name')
        target = request.POST.get('target_amount')
        
        # 2. Safety check: make sure they actually typed something!
        if goal_name and target:
            # 3. Save it to the database linked to this specific user
            SavingsGoal.objects.create(
                user=request.user,
                name=goal_name,
                target_amount=target,
                current_amount=0 # Starts at 0!
            )
            
    # 4. Instantly redirect them back to the dashboard to see it
    return redirect('dashboard')


def add_to_goal(request, goal_id):

    if request.method == 'POST':
        # 1. Find the exact goal
        goal = get_object_or_404(SavingsGoal, id=goal_id, user=request.user)
        added_amount = request.POST.get('amount')
        
        if added_amount and Decimal(added_amount) > 0:
            amount_decimal = Decimal(added_amount)
            
            # 2. Update the Goal's progress bar
            goal.current_amount += amount_decimal
            goal.save()
            
            # 3. THE MAGIC: Find or create a dedicated "Savings" category
            # (If your Category model requires a user, add user=request.user inside the parentheses below)
            savings_category, created = Category.objects.get_or_create(
                name="💰 Savings Goals",
                user=request.user
            )
            
            # 4. Automatically generate the Expense transaction!
            Expense.objects.create(
                user=request.user,
                amount=amount_decimal,
                category=savings_category,
                description=f"Funded Goal: {goal.name}",
                date=timezone.now().date()
            )
            
    return redirect('dashboard')

def delete_goal(request, goal_id):
    # Find the goal and delete it
    goal = get_object_or_404(SavingsGoal, id=goal_id, user=request.user)
    goal.delete()
    return redirect('dashboard')

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
@csrf_exempt
def scan_receipt(request):
    if request.method == 'POST' and request.FILES.get('receipt'):
        receipt_file = request.FILES['receipt']
        
        try:
            # 1. Open and grayscale the image
            img = Image.open(receipt_file).convert('L') 
            scanned_text = pytesseract.image_to_string(img)
            
            # 2. THE NEW BRAIN: Check for a Dollar sign BEFORE we clean the text
            is_usd = '$' in scanned_text or 'USD' in scanned_text
            
            # 3. Now clean the text so the Regex doesn't get confused
            clean_text = scanned_text.replace('$', '').replace(',', '')
            
            # 4. Find the numbers
            amounts = re.findall(r'\b\d+\.\d{2}\b', clean_text)
            if not amounts:
                amounts = re.findall(r'\b\d+\b', clean_text)
            
            if amounts:
                float_amounts = [float(a) for a in amounts]
                valid_amounts = [a for a in float_amounts if a < 10000]
                
                if valid_amounts:
                    total_amount = max(valid_amounts)
                    
                    # 5. LIVE CURRENCY CONVERSION!
                    if is_usd:
                        try:
                            # Fetch today's live exchange rate from a free public API
                            api_response = requests.get('https://api.exchangerate-api.com/v4/latest/USD')
                            inr_rate = api_response.json()['rates']['INR']
                            
                            # Multiply $31.39 by today's rate (e.g., ~82.7)
                            total_amount = round(total_amount * inr_rate, 2)
                        except:
                            # Fallback rate just in case the internet disconnects
                            total_amount = round(total_amount * 83.50, 2) 

                    return JsonResponse({'success': True, 'amount': total_amount})
                
            return JsonResponse({'success': False, 'error': 'Could not read any valid numbers'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'Invalid request'})
from .models import UserProfile # Make sure to import the new model!

def upload_profile_picture(request):
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        # Get the user's backpack
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # Save the new photo!
        profile.profile_picture = request.FILES['profile_picture']
        profile.save()
        
    # Send them right back to where they came from (e.g., settings or profile page)
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


from django.contrib.auth.decorators import login_required
from .forms import UserProfileForm, UserUpdateForm # Make sure both are imported!

@login_required
def profile(request):
    user_profile = request.user.userprofile
    
    
    if request.method == 'POST':
        # Grab data for BOTH forms
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
        
        # If both forms are filled out correctly, save them both!
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            return redirect('profile')
    else:
        # Pre-fill both forms with current data
        u_form = UserUpdateForm(instance=request.user)
        p_form = UserProfileForm(instance=user_profile)
        
    return render(request, 'expenses/profile.html', {
        'u_form': u_form,
        'p_form': p_form,
        'profile': user_profile,
        
    })

@login_required
def update_budget(request, budget_id):
    if request.method == 'POST':
        # Find the specific budget row and make sure it belongs to the logged-in user
        budget = get_object_or_404(CategoryBudget, id=budget_id, user=request.user)
        new_limit = request.POST.get('limit')
        
        if new_limit and float(new_limit) >= 0:
            budget.limit = new_limit
            budget.save()
            
    return redirect('settings')

from google.genai import types
from google import genai # NEW IMPORT!
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

# Initialize the new Client architecture
# IMPORTANT: Put your actual API key back in here!
client = genai.Client(api_key="AIzaSyB5Nv5KosLP1ITOQxgsFrjHxHQCWGp8rpc")

@csrf_exempt
@login_required
def ai_chat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')

            # Gather the user's financial context
            recent_expenses = Expense.objects.filter(user=request.user).order_by('-date', '-id')[:15]
            
            expense_data_str = "Here are the user's recent expenses:\n"
            for exp in recent_expenses:
                cat_name = exp.category.name if exp.category else "Uncategorized"
                expense_data_str += f"- {exp.date}: {cat_name} - {exp.amount} ({exp.description})\n"

            master_prompt = f"""
            You are a brilliant, friendly, and concise financial advisor for an expense tracking app.
            Analyze the user's data provided below to answer their question. Keep your answer under 3-4 short sentences. 
            Be encouraging, but point out if they are spending too much on one specific thing. Do not use markdown formatting like asterisks.
            
            {expense_data_str}
            
            User's Question: {user_message}
            """

            # NEW SYNTAX: Tell the client to use the 2.5 flash model
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=master_prompt,
            )

            return JsonResponse({'success': True, 'reply': response.text})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request'})


@csrf_exempt
@login_required
def predict_category(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            description = data.get('description', '')

            # 1. Fetch the user's specific categories
            user_categories = Category.objects.filter(user=request.user)
            category_names = [cat.name for cat in user_categories]

            if not category_names:
                return JsonResponse({'success': False, 'error': 'No categories exist yet.'})

            prompt = f"""
            You are a smart financial categorizer. 
            The user bought something described as: "{description}"
            Here are their exact database categories: {', '.join(category_names)}
            
            Which of those categories is the best fit? 
            Reply with EXACTLY and ONLY the category name. Do not add any punctuation, quotes, or extra words.
            """

            # 2. Ask Gemini (Using a simplified config dictionary to prevent import crashes!)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={
                    "max_output_tokens": 10,
                    "temperature": 0.1 
                }
            )
            
            predicted_category = response.text.strip()
            
            # Print the AI's thought process to your terminal!
            print(f"✅ AI Successfully Predicted: {predicted_category}") 
            
            return JsonResponse({'success': True, 'category': predicted_category})

        except Exception as e:
            # THIS IS THE MAGIC LINE: It will print the exact reason it failed to your VS Code terminal!
            print(f"❌ AI ERROR: {str(e)}") 
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request'})
            

           