"""
Models for CodeLens Application
Defines User Profiles, Code Analysis, Analysis History, and 3NF Relational Data
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# -------------------- Choices -------------------- #
ANALYSIS_STATUS = [
    ('pending', 'Pending'),
    ('completed', 'Completed'),
    ('error', 'Error'),
]

# -------------------- User Profile -------------------- #
class UserProfile(models.Model):
    """Extended user profile"""
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('ultra', 'Ultra'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def avatar_url(self):
        """Fetches social account avatar URL dynamically without extra DB schema fields."""
        try:
            from allauth.socialaccount.models import SocialAccount
            social_account = SocialAccount.objects.filter(user=self.user).first()
            if social_account:
                return social_account.get_avatar_url()
        except Exception:
            pass
        return None

    @property
    def total_analyses(self):
        """Calculated dynamically to maintain strict 3NF"""
        return self.user.analyses.count()

    @property
    def daily_analyses_limit(self):
        """Returns the daily analyses quota based on plan type"""
        if self.plan_type == 'pro':
            return 200
        elif self.plan_type == 'ultra':
            return 999999  # Unlimited
        return 30

    def daily_analyses_count(self):
        """Calculate analyses completed in the rolling last 24 hours in strict 3NF"""
        time_threshold = timezone.now() - timezone.timedelta(hours=24)
        return self.user.analyses.filter(created_at__gte=time_threshold).count()

    def has_quota(self):
        """Check if user has remaining analysis quota for today"""
        return self.daily_analyses_count() < self.daily_analyses_limit

    def __str__(self):
        return f"{self.user.username} - Profile ({self.plan_type})"

# -------------------- Code Analysis -------------------- #
class CodeAnalysis(models.Model):
    """Core analysis record"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='analyses')
    code_input = models.TextField()
    analysis_number = models.IntegerField(default=1)  # Per-user analysis counter (1, 2, 3...)
    
    status = models.CharField(max_length=20, choices=ANALYSIS_STATUS, default='pending')
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        """Auto-increment analysis_number per user"""
        if not self.pk:  # Only on creation
            last_analysis = CodeAnalysis.objects.filter(user=self.user).order_by('-analysis_number').first()
            self.analysis_number = (last_analysis.analysis_number + 1) if last_analysis else 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Analysis #{self.analysis_number} by {self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

# -------------------- Analysis History -------------------- #
class AnalysisHistory(models.Model):
    """Tracks analysis history for pagination and filtering"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='history')
    analysis = models.OneToOneField(CodeAnalysis, on_delete=models.CASCADE, related_name='history_entry')
    
    title = models.CharField(max_length=255, blank=True)
    tags = models.CharField(max_length=255, blank=True)
    
    is_starred = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    viewed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Analysis Histories'

    def __str__(self):
        return f"History: {self.user.username} - {self.title or self.analysis.id}"

# =====================================================================
# 3NF RELATIONAL TABLES (Replacing the old JSONFields)
# =====================================================================

class AnalysisError(models.Model):
    """Stores individual syntax/runtime errors found in the code"""
    analysis = models.ForeignKey(CodeAnalysis, on_delete=models.CASCADE, related_name='errors_detected')
    error_type = models.CharField(max_length=100)
    message = models.TextField()
    line_number = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.error_type} in Analysis {self.analysis.id}"

class OOPConcept(models.Model):
    """Stores individual OOP concepts detected in the code"""
    analysis = models.ForeignKey(CodeAnalysis, on_delete=models.CASCADE, related_name='oop_concepts')
    concept_name = models.CharField(max_length=100)
    details = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.concept_name} in Analysis {self.analysis.id}"

class CodeSmell(models.Model):
    """Stores individual code smells detected"""
    analysis = models.ForeignKey(CodeAnalysis, on_delete=models.CASCADE, related_name='code_smells')
    smell_type = models.CharField(max_length=100)
    detected_value = models.CharField(max_length=255, blank=True)
    line_number = models.IntegerField(null=True, blank=True)
    suggestion = models.TextField()

    def __str__(self):
        return f"{self.smell_type} in Analysis {self.analysis.id}"

class RefactoringSuggestion(models.Model):
    """Stores AI-generated refactoring suggestions"""
    analysis = models.ForeignKey(CodeAnalysis, on_delete=models.CASCADE, related_name='refactoring_suggestions')
    priority = models.CharField(max_length=50, default='medium')
    suggestion_text = models.TextField()
    refactored_code = models.TextField()

    def __str__(self):
        return f"Refactoring for Analysis {self.analysis.id} ({self.priority})"


# -------------------- Bug Reports -------------------- #
class BugReport(models.Model):
    """Stores user-submitted bug reports and system diagnostics telemetry"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bug_reports')
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=50, default='other')
    severity = models.CharField(max_length=20, default='low')
    steps = models.TextField(blank=True)
    description = models.TextField()
    diagnostics = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bug '{self.title}' [{self.severity.upper()}] by {self.user.username}"