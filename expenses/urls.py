# expenses/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add-expense/', views.add_expense, name='add_expense'),
    path('edit/<int:id>/', views.edit_expense, name='edit_expense'),
    path('delete/<int:id>/', views.delete_expense, name='delete_expense'),
    path('export/', views.export_csv, name='export_csv'),
    path('export/', views.export_csv, name='export_csv'),
    
    # NEW PATH
    path('settings/', views.settings, name='settings'),
    path('history/', views.history, name='history'),
    
    path('export-pdf/', views.export_pdf, name='export_pdf'),
    path('categories/', views.manage_categories, name='manage_categories'),
    path('add-goal/', views.add_goal, name='add_goal'),
    path('add-to-goal/<int:goal_id>/', views.add_to_goal, name='add_to_goal'),
    path('delete-goal/<int:goal_id>/', views.delete_goal, name='delete_goal'),
    path('scan-receipt/', views.scan_receipt, name='scan_receipt'),
    path('upload-profile-picture/', views.upload_profile_picture, name='upload_profile_picture'),
    path('profile/', views.profile, name='profile'),
    path('update-budget/<int:budget_id>/', views.update_budget, name='update_budget'),
    path('ai-chat/', views.ai_chat, name='ai_chat'),
    # Add this right below your ai-chat url!
    path('predict-category/', views.predict_category, name='predict_category'),
]