"""
URL Configuration for analyzer app
Routes for authentication, analysis, and history
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('analyzer/', views.analyzer_page, name='analyzer'),
    path('profile/', views.profile_page, name='profile'),
    path('settings/', views.settings_page, name='settings'),
    path('settings/delete-account/', views.delete_account, name='delete_account'),
    path('about/', views.about_page, name='about'),
    path('help/', views.help_page, name='help'),
    path('subscription/', views.subscription_page, name='subscription'),
    path('upgrade-ultra/', views.upgrade_ultra_page, name='upgrade_ultra'),
    path('usages/', views.usage_limits_page, name='usage_limits'),
    path('login/', views.signin, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.signout, name='logout'),
    path('analyze/', views.analyze_code, name='analyze'),
    path('analyze-github/', views.analyze_github, name='analyze_github'),
    path('functionalities/', views.functionalities, name='functionalities'),
    path('history/', views.history, name='history'),
    path('api/analysis/<int:analysis_id>/', views.get_analysis_detail, name='analysis_detail'),
    path('api/history/<int:history_id>/delete/', views.delete_history, name='delete_history'),
    path('api/history/clear-all/', views.clear_all_history, name='clear_all_history'),
    path('api/analysis/<int:analysis_id>/star/', views.star_analysis, name='star_analysis'),
    path('ai-explain/', views.ai_explain, name='ai_explain'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
