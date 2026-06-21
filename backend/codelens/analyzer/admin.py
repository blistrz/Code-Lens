"""Django Admin Configuration for CodeLens"""
from django.contrib import admin
from .models import UserProfile, CodeAnalysis, AnalysisHistory, BugReport


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_analyses', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    list_filter = ['created_at']


@admin.register(CodeAnalysis)
class CodeAnalysisAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    search_fields = ['user__username', 'code_input']


@admin.register(AnalysisHistory)
class AnalysisHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'is_starred', 'created_at']
    list_filter = ['is_starred', 'is_deleted', 'created_at']
    readonly_fields = ['created_at']
    search_fields = ['user__username', 'title', 'tags']


@admin.register(BugReport)
class BugReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'category', 'severity', 'created_at']
    list_filter = ['severity', 'category', 'created_at']
    search_fields = ['title', 'user__username', 'description', 'steps']
    readonly_fields = ['created_at']
