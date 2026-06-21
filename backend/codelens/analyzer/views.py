"""
Views for CodeLens Application
Handles authentication, code analysis, and history management
"""

import os
import ast
import json
import re
import requests
from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth.models import User
import traceback
# Make sure ALL of these are imported from .models
from .models import UserProfile, CodeAnalysis, AnalysisHistory, AnalysisError, CodeSmell, OOPConcept, RefactoringSuggestion, BugReport
from .error_detector import detect_errors, extract_oop_features, detect_oop_design_smells
from django.db.models import Count
from django.db.models.functions import TruncDate
from datetime import timedelta
from django.utils import timezone
import time
from django.db import connection
import json

# ==========================================
# 🤖 AI SURGEON CONFIGURATION (HUGGING FACE)
# ==========================================
# 🛑 PASTE YOUR NEW SECURE TOKEN HERE:
HF_TOKEN = "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"
API_URL = "https://router.huggingface.co/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

def generate_refactored_code(smelly_code, ai_model='qwen-32b', refactor_level='balanced'):
    """Sends code to Hugging Face models for generative refactoring based on preferences."""
    # Map selection to endpoint model name
    model_mapping = {
        'qwen-32b': 'Qwen/Qwen2.5-Coder-32B-Instruct',
        'codellama-34b': 'codellama/CodeLlama-34b-Instruct-hf',
        'mistral-7b': 'mistralai/Mistral-7B-Instruct-v0.3',
        'llama-3-8b': 'meta-llama/Meta-Llama-3-8B-Instruct'
    }
    target_model = model_mapping.get(ai_model, 'Qwen/Qwen2.5-Coder-32B-Instruct')

    # Construct custom system instruction based on refactor_level
    if refactor_level == 'conservative':
        system_content = (
            "You are a senior Python developer. Refactor the provided code to fix structural smells. "
            "Make only the most critical, safe, and minimal changes to fix smells; preserve the existing design and logic as much as possible. "
            "Output ONLY the raw, refactored Python code. Do not include explanations, intro text, or markdown code blocks."
        )
    elif refactor_level == 'creative':
        system_content = (
            "You are a senior Python developer. Refactor the provided code using modern design patterns, object-oriented concepts, and clean coding principles. "
            "Be highly creative in reorganizing the code for optimal readability, performance, and structure. "
            "Output ONLY the raw, refactored Python code. Do not include explanations, intro text, or markdown code blocks."
        )
    else:  # balanced
        system_content = (
            "You are a senior Python developer. Refactor the provided code to fix structural smells. "
            "Output ONLY the raw, refactored Python code. Do not include explanations, intro text, or markdown code blocks."
        )

    try:
        payload = {
            "model": target_model,
            "messages": [
                {
                    "role": "system", 
                    "content": system_content
                },
                {"role": "user", "content": f"Refactor this:\n{smelly_code}"}
            ],
            "max_tokens": 4096
        }
        response = requests.post(API_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        elif response.status_code == 503:
            return "# AI Surgeon is waking up. Please click Analyze again in 15 seconds."
        else:
            return f"# API Error {response.status_code}: {response.text}"
    except Exception as e:
        return f"# System Error: {repr(e)}"

# ==========================================
# 🌐 DJANGO VIEWS & ROUTING
# ==========================================

def _social_login_enabled():
    """Returns True only when OAuth credentials are actually configured."""
    from django.conf import settings
    providers = getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {})
    google_ok = bool(providers.get('google', {}).get('APP', {}).get('client_id', '').strip())
    github_ok = bool(providers.get('github', {}).get('APP', {}).get('client_id', '').strip())
    return {'google': google_ok, 'github': github_ok, 'any': google_ok or github_ok}

@ensure_csrf_cookie
def home(request):
    return render(request, 'HomePage.html')

@login_required(login_url='login')
@ensure_csrf_cookie
def analyzer_page(request):
    return render(request, 'analyzer.html')

@login_required(login_url='login')
@ensure_csrf_cookie
def profile_page(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_profile':
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            
            # Simple validation
            if not email:
                messages.error(request, "Email address is required.")
            else:
                request.user.first_name = first_name
                request.user.last_name = last_name
                request.user.email = email
                request.user.save()
                messages.success(request, "Profile details updated successfully.")
            return redirect('profile')
            
    context = {
        'profile': profile,
    }
    return render(request, 'profile.html', context)


@login_required(login_url='login')
@ensure_csrf_cookie
def settings_page(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'change_password':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            
            if not request.user.check_password(current_password):
                messages.error(request, "Incorrect current password.")
            elif not new_password or new_password != confirm_password:
                messages.error(request, "New passwords do not match or are empty.")
            elif len(new_password) < 6:
                messages.error(request, "Password must be at least 6 characters.")
            else:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user) # Keep user logged in
                messages.success(request, "Password updated successfully.")
            return redirect('settings')
            
    context = {
        'profile': profile,
    }
    return render(request, 'settings.html', context)


@login_required(login_url='login')
@ensure_csrf_cookie
def help_page(request):
    """Renders the unified Help, Privacy, and Bug Reporting page."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'report_bug':
            bug_title = request.POST.get('bug_title', '').strip()
            bug_desc = request.POST.get('bug_description', '').strip()
            category = request.POST.get('category', 'other').strip()
            severity = request.POST.get('severity', 'low').strip()
            steps = request.POST.get('steps', '').strip()
            diagnostics = request.POST.get('diagnostics', '').strip()
            
            if not bug_title or not bug_desc:
                messages.error(request, "Please fill in all required fields to report a bug.")
            else:
                # Print structured telemetry directly to server logs
                print("\n" + "="*60)
                print("🐛 NEW INCOMING BUG REPORT (TELEMETRY CAPTURED) 🐛")
                print("="*60)
                print(f"Submitted By : User '{request.user.username}' <{request.user.email}>")
                print(f"Bug Title    : {bug_title}")
                print(f"Category     : {category.upper()}")
                print(f"Severity     : {severity.upper()}")
                print(f"Steps        :\n{steps}")
                print(f"Description  :\n{bug_desc}")
                print(f"Diagnostics  :\n{diagnostics}")
                print("="*60 + "\n")
                # Save to Database
                BugReport.objects.create(
                    user=request.user,
                    title=bug_title,
                    category=category,
                    severity=severity,
                    steps=steps,
                    description=bug_desc,
                    diagnostics=diagnostics
                )

                messages.success(
                    request, 
                    f"[{severity.upper()}] Bug '{bug_title}' successfully reported with telemetry checklist! Standard tickets are processed within 24 hours."
                )
            return redirect('help')
            
    context = {
        'profile': profile,
    }
    return render(request, 'help.html', context)

@login_required(login_url='login')
@require_http_methods(["POST"])
def delete_account(request):
    """Permanently deletes the authenticated user's account and all associated data."""
    user = request.user
    logout(request)
    user.delete()
    messages.success(request, "Your account has been permanently deleted.")
    return redirect('home')


@login_required(login_url='login')
@ensure_csrf_cookie
def subscription_page(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_plan':
            new_plan = request.POST.get('plan_type', 'free').strip().lower()
            if new_plan in ['free', 'pro', 'ultra']:
                profile.plan_type = new_plan
                profile.save()
                messages.success(request, f"Subscription successfully updated to {new_plan.title()}!")
            else:
                messages.error(request, "Invalid plan selection.")
            return redirect('subscription')
            
    used = profile.daily_analyses_count()
    limit = profile.daily_analyses_limit
    percent = min(100, int((used / limit) * 100)) if limit > 0 else 100
    
    context = {
        'profile': profile,
        'used_today': used,
        'limit_today': limit if limit < 999999 else 'Unlimited',
        'percent_today': percent,
    }
    return render(request, 'subscription.html', context)

@login_required(login_url='login')
@ensure_csrf_cookie
def upgrade_ultra_page(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'upgrade_ultra':
            profile.plan_type = 'ultra'
            profile.save()
            messages.success(request, "Welcome to CodeLens Ultra! Your premium benefits are active immediately.")
            return redirect('upgrade_ultra')
            
    context = {
        'profile': profile,
    }
    return render(request, 'upgrade_ultra.html', context)

@login_required(login_url='login')
@ensure_csrf_cookie
def usage_limits_page(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    used = profile.daily_analyses_count()
    limit = profile.daily_analyses_limit
    percent = min(100, int((used / limit) * 100)) if limit > 0 else 100
    
    context = {
        'profile': profile,
        'used_today': used,
        'limit_today': limit if limit < 999999 else 'Unlimited',
        'percent_today': percent,
    }
    return render(request, 'usage_limits.html', context)

def about_page(request):
    return render(request, 'about.html')

def signin(request):
    # Redirect users who are already logged in
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()  # Can be username or email
        password = request.POST.get('password', '')

        # Try to authenticate with identifier as username first
        user = authenticate(request, username=identifier, password=password)
        
        # If that fails, try to find a user by email and authenticate
        if user is None:
            try:
                user_obj = User.objects.get(email=identifier)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            return render(request, 'login.html', {
                'error': 'Invalid username, email or password. Please try again.',
                'social': _social_login_enabled(),
            })

    return render(request, 'login.html', {'social': _social_login_enabled()})

def signup(request):
    # Redirect users who are already logged in
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        username = request.POST.get('username', '').strip() # Added username
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '') # Added confirm

        # 1. Check for empty fields
        if not all([name, username, email, password, password_confirm]):
            return render(request, 'signup.html', {'error': 'All fields are required.', 'social': _social_login_enabled()})

        # 2. Check if passwords match
        if password != password_confirm:
            return render(request, 'signup.html', {'error': 'Passwords do not match.', 'social': _social_login_enabled()})

        # 3. Check if username is already taken
        if User.objects.filter(username=username).exists():
            return render(request, 'signup.html', {'error': 'This username is already taken.', 'social': _social_login_enabled()})

        # 4. Check if email is already registered
        if User.objects.filter(email=email).exists():
            return render(request, 'signup.html', {'error': 'An account with this email already exists.', 'social': _social_login_enabled()})

        # Split name into first and last name for proper profile display
        first_name = name
        last_name = ''
        if ' ' in name:
            first_name, last_name = name.split(' ', 1)

        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            UserProfile.objects.create(user=user)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('home')

        except IntegrityError:
            return render(request, 'signup.html', {'error': 'A database error occurred. Please try again.', 'social': _social_login_enabled()})

    return render(request, 'signup.html', {'social': _social_login_enabled()})

def signout(request):
    logout(request)
    return redirect('home')

def _smart_title(code: str, prefix: str = '') -> str:
    """
    Generate a human-readable history title from code.
    Tries to extract class & function names via AST.
    Falls back to a cleaned first non-empty line.
    """
    names = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith('_'):  # skip private helpers
                    names.append(node.name)
                if len(names) >= 4:
                    break
    except SyntaxError:
        pass

    if names:
        label = ', '.join(names[:4])
        if len(names) > 4:
            label += f' +{len(names)-4} more'
        return f'{prefix + " · " if prefix else ""}{label}'

    # Fallback: first meaningful line of code, cleaned up
    for line in code.splitlines():
        line = line.strip().lstrip('#').strip()
        if line and not line.startswith('import') and not line.startswith('from'):
            return f'{prefix + " · " if prefix else ""}' + line[:60]

    return prefix or 'Untitled Analysis'


@login_required(login_url='login')
@require_http_methods(["POST"])
def analyze_code(request):
    try:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if not profile.has_quota():
            return JsonResponse({
                'error': f'Daily limit reached! You have used all {profile.daily_analyses_limit} free analyses for today. Please upgrade your plan in Settings to continue.'
            }, status=403)

        data = json.loads(request.body)
        code_input = data.get('code', '').strip()
        if not code_input:
            return JsonResponse({'error': 'Code cannot be empty'}, status=400)

        # Extract user preferences
        ai_model = data.get('ai_model', 'qwen-32b')
        refactor_level = data.get('refactor_level', 'balanced')
        smells_threshold = data.get('smells_threshold', 'verbose')

        # Run your AI & Python analysis logic
        results = perform_code_analysis(
            code_input,
            ai_model=ai_model,
            refactor_level=refactor_level,
            smells_threshold=smells_threshold
        )

        # 1. Save Main Analysis Entry
        analysis = CodeAnalysis.objects.create(
            user=request.user,
            code_input=code_input,
            status='completed'
        )

        # 2. Save Errors Relational Rows
        for error in results.get('errors', []):
            AnalysisError.objects.create(
                analysis=analysis,
                error_type=error.get('type', 'SyntaxError') if isinstance(error, dict) else 'Error',
                message=error.get('message', str(error)) if isinstance(error, dict) else str(error),
                line_number=error.get('line') if isinstance(error, dict) else None
            )

        # 3. Save Code Smells Relational Rows
        for smell in results.get('code_smells', []):
            CodeSmell.objects.create(
                analysis=analysis,
                smell_type=smell.get('type', 'Unknown'),
                detected_value=smell.get('value', ''),
                line_number=smell.get('line'),
                suggestion=smell.get('suggestion', '')
            )

       # 4. Save OOP Concepts (UPDATED)
        oop_design_smells = detect_oop_design_smells(
            analysis.code_input,
            results.get('oop_concepts', []),
        )
        for concept in results.get('oop_concepts', []):
            if isinstance(concept, dict):
                concept_name = concept.get('name', 'Unknown Class')
                
                # Build a beautifully formatted text block for the 'details' column
                details_lines = []
                
                # 1. Grab inherited classes
                bases = concept.get('bases', [])
                if bases:
                    details_lines.append(f"Inherits From: {', '.join(bases)}")
                
                # 2. Grab methods
                methods = concept.get('methods', [])
                if methods:
                    details_lines.append(f"Methods Detected ({len(methods)}):")
                    for method in methods:
                        m_name = method.get('name', 'unknown')
                        m_type = method.get('type', 'method')
                        details_lines.append(f"  → {m_name}()  [{m_type}]")

                class_notes = [
                    s for s in oop_design_smells
                    if s.get('class_name') == concept_name
                ]
                if class_notes:
                    details_lines.append("")
                    details_lines.append("Architecture notes:")
                    for note in class_notes:
                        details_lines.append(f"  ⚠ {note['type']}")
                        details_lines.append(f"    {note['suggestion']}")
                
                # Join the lines with a line break
                details_text = "\n".join(details_lines) if details_lines else "Basic class definition."
            else:
                concept_name = str(concept)
                details_text = ""

            OOPConcept.objects.create(
                analysis=analysis,
                concept_name=concept_name,
                details=details_text
            )

        # 5. Save Refactoring Suggestions
        for sugg in results.get('refactoring_suggestions', []):
            RefactoringSuggestion.objects.create(
                analysis=analysis,
                priority=sugg.get('priority', 'high'),
                suggestion_text=sugg.get('suggestion', ''),
                refactored_code=sugg.get('refactored_code', '')
            )

        # 6. Create History Entry — with a human-readable smart title
        AnalysisHistory.objects.create(
            user=request.user,
            analysis=analysis,
            title=_smart_title(code_input)
        )

        # Add success message with remaining quota
        left = max(0, profile.daily_analyses_limit - profile.daily_analyses_count())
        if profile.plan_type in ['free', 'pro']:
            plan_name = "Pro" if profile.plan_type == 'pro' else "Free"
            messages.success(request, f"Analysis complete! You have {left} analyses left on your {plan_name} plan for today.")

        return JsonResponse({'success': True, 'analysis_id': analysis.id})

    except Exception as e:
        # --- THE MAGIC BULLET ---
        # This will bypass the JSON hide and print the exact error to your terminal
        print("\n" + "!"*50)
        print("🚨 CRITICAL CRASH IN ANALYZE_CODE 🚨")
        traceback.print_exc()
        print("!"*50 + "\n")
        
        return JsonResponse({'error': str(e)}, status=500)

# ==========================================
# 🐙 GITHUB / GIST INTEGRATION
# ==========================================

def _github_headers(token=None):
    """Build GitHub API headers, optionally with a PAT for private repos."""
    h = {'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'CodeLens-App'}
    if token:
        h['Authorization'] = f'token {token}'
    return h

def _fetch_repo_python_files(owner, repo, token=None, max_files=10):
    """
    Fetches up to `max_files` Python files from the default branch of a GitHub repo.
    Returns list of {'path': str, 'content': str} dicts.
    """
    api = f'https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1'
    resp = requests.get(api, headers=_github_headers(token), timeout=15)
    if resp.status_code == 404:
        return None, 'Repository not found or is private. Supply a GitHub token for private repos.'
    if resp.status_code != 200:
        return None, f'GitHub API error {resp.status_code}.'

    tree = resp.json().get('tree', [])
    py_blobs = [
        item for item in tree
        if item.get('type') == 'blob' and item.get('path', '').endswith('.py')
    ][:max_files]

    if not py_blobs:
        return None, 'No Python (.py) files found in this repository.'

    files = []
    for blob in py_blobs:
        raw_url = f'https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{blob["path"]}'
        r = requests.get(raw_url, headers=_github_headers(token), timeout=10)
        if r.status_code == 200:
            files.append({'path': blob['path'], 'content': r.text})
    return files, None

def _fetch_gist_python_files(gist_id, token=None):
    """Fetches all Python files from a public or private GitHub Gist."""
    api = f'https://api.github.com/gists/{gist_id}'
    resp = requests.get(api, headers=_github_headers(token), timeout=10)
    if resp.status_code == 404:
        return None, 'Gist not found or is private.'
    if resp.status_code != 200:
        return None, f'GitHub API error {resp.status_code}.'

    gist_files = resp.json().get('files', {})
    files = []
    for filename, meta in gist_files.items():
        if filename.endswith('.py'):
            raw_url = meta.get('raw_url')
            if raw_url:
                r = requests.get(raw_url, timeout=10)
                if r.status_code == 200:
                    files.append({'path': filename, 'content': r.text})
    if not files:
        return None, 'No Python (.py) files found in this Gist.'
    return files, None

@login_required(login_url='login')
@require_http_methods(['POST'])
def analyze_github(request):
    """
    Accepts a GitHub repo URL or Gist URL, fetches Python files,
    concatenates them with file headers, and runs the full analysis pipeline.
    """
    try:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if not profile.has_quota():
            return JsonResponse({
                'error': f'Daily limit reached! You have used all {profile.daily_analyses_limit} free analyses for today. Please upgrade your plan in Settings to continue.'
            }, status=403)

        data = json.loads(request.body)
        url   = data.get('url', '').strip()
        token = data.get('token', '').strip() or None

        # Extract user preferences
        ai_model = data.get('ai_model', 'qwen-32b')
        refactor_level = data.get('refactor_level', 'balanced')
        smells_threshold = data.get('smells_threshold', 'verbose')

        if not url:
            return JsonResponse({'error': 'URL cannot be empty.'}, status=400)

        files = None
        err   = None

        # ── Gist URL pattern: gist.github.com/<user>/<gist_id>
        gist_match = re.match(
            r'https?://gist\.github\.com/[^/]+/([a-f0-9]+)', url, re.IGNORECASE
        )
        # ── Repo URL pattern: github.com/<owner>/<repo>
        repo_match = re.match(
            r'https?://github\.com/([^/]+)/([^/?\s#]+)', url, re.IGNORECASE
        )

        if gist_match:
            gist_id = gist_match.group(1)
            files, err = _fetch_gist_python_files(gist_id, token)
        elif repo_match:
            owner, repo = repo_match.group(1), repo_match.group(2).rstrip('.git')
            files, err = _fetch_repo_python_files(owner, repo, token)
        else:
            return JsonResponse({'error': 'Invalid URL. Provide a GitHub repo or Gist URL.'}, status=400)

        if err:
            return JsonResponse({'error': err}, status=400)

        # Concatenate all files with clear separators
        combined_code = '\n\n'.join(
            f'# ── File: {f["path"]} ──\n{f["content"]}'
            for f in files
        )

        # Run the existing analysis pipeline on combined code
        results = perform_code_analysis(
            combined_code,
            ai_model=ai_model,
            refactor_level=refactor_level,
            smells_threshold=smells_threshold
        )

        analysis = CodeAnalysis.objects.create(
            user=request.user,
            code_input=combined_code,
            status='completed'
        )
        file_paths = ', '.join(f['path'] for f in files)

        for error in results.get('errors', []):
            AnalysisError.objects.create(
                analysis=analysis,
                error_type=error.get('type', 'SyntaxError') if isinstance(error, dict) else 'Error',
                message=error.get('message', str(error)) if isinstance(error, dict) else str(error),
                line_number=error.get('line') if isinstance(error, dict) else None
            )
        for smell in results.get('code_smells', []):
            CodeSmell.objects.create(
                analysis=analysis,
                smell_type=smell.get('type', 'Unknown'),
                detected_value=smell.get('value', ''),
                line_number=smell.get('line'),
                suggestion=smell.get('suggestion', '')
            )
        oop_design_smells = detect_oop_design_smells(combined_code, results.get('oop_concepts', []))
        for concept in results.get('oop_concepts', []):
            if isinstance(concept, dict):
                concept_name = concept.get('name', 'Unknown Class')
                details_lines = []
                bases = concept.get('bases', [])
                if bases:
                    details_lines.append(f"Inherits From: {', '.join(bases)}")
                methods = concept.get('methods', [])
                if methods:
                    details_lines.append(f"Methods Detected ({len(methods)}):")
                    for method in methods:
                        details_lines.append(f"  → {method.get('name','unknown')}()  [{method.get('type','method')}]")
                class_notes = [s for s in oop_design_smells if s.get('class_name') == concept_name]
                if class_notes:
                    details_lines.append("")
                    details_lines.append("Architecture notes:")
                    for note in class_notes:
                        details_lines.append(f"  ⚠ {note['type']}")
                        details_lines.append(f"    {note['suggestion']}")
                details_text = "\n".join(details_lines) if details_lines else "Basic class definition."
            else:
                concept_name, details_text = str(concept), ""
            OOPConcept.objects.create(analysis=analysis, concept_name=concept_name, details=details_text)
        for sugg in results.get('refactoring_suggestions', []):
            RefactoringSuggestion.objects.create(
                analysis=analysis,
                priority=sugg.get('priority', 'high'),
                suggestion_text=sugg.get('suggestion', ''),
                refactored_code=sugg.get('refactored_code', '')
            )

        AnalysisHistory.objects.create(
            user=request.user,
            analysis=analysis,
            title=_smart_title(combined_code, prefix=f'GitHub: {url[:40]}')
        )

        # Add success message with remaining quota
        left = max(0, profile.daily_analyses_limit - profile.daily_analyses_count())
        if profile.plan_type in ['free', 'pro']:
            plan_name = "Pro" if profile.plan_type == 'pro' else "Free"
            messages.success(request, f"Analysis complete! You have {left} analyses left on your {plan_name} plan for today.")

        return JsonResponse({
            'success': True,
            'analysis_id': analysis.id,
            'files_analyzed': len(files),
            'file_paths': file_paths,
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


class VerboseSmellsVisitor(ast.NodeVisitor):
    def __init__(self):
        self.smells = []
        self.in_function = False
        self.in_class = False

    def visit_ClassDef(self, node):
        was_in_class = self.in_class
        self.in_class = True
        self.generic_visit(node)
        self.in_class = was_in_class

    def visit_FunctionDef(self, node):
        was_in_func = self.in_function
        self.in_function = True
        
        # Check for empty / dead-code function block (only "pass" or empty)
        statements = [s for s in node.body if not (
            isinstance(s, ast.Expr) and 
            isinstance(s.value, ast.Constant) and 
            isinstance(s.value.value, str)
        )]
        if len(statements) == 1 and isinstance(statements[0], ast.Pass):
            self.smells.append({
                'type': 'Empty Function / Dead Code',
                'value': f"Function '{node.name}' has an empty block (only 'pass')",
                'line': node.lineno,
                'suggestion': f"Implement logic for '{node.name}' or remove the function if it is unused."
            })
        elif len(statements) == 0:
            self.smells.append({
                'type': 'Empty Function / Dead Code',
                'value': f"Function '{node.name}' is empty",
                'line': node.lineno,
                'suggestion': f"Implement logic for '{node.name}' or remove the function if it is unused."
            })

        self.generic_visit(node)
        self.in_function = was_in_func

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Assign(self, node):
        # 1. Check for global baseline integer literals
        if not self.in_function and not self.in_class:
            if len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                    if isinstance(node.value.value, (int, float)):
                        self.smells.append({
                            'type': 'Magic Number',
                            'value': f"Literal value '{node.value.value}' (Global baseline)",
                            'line': node.lineno,
                            'suggestion': f"Extract raw global literal '{node.value.value}' to an environment variable or configuration file."
                        })
        
        # 2. Check for camelCase variables in assignments
        def check_name(name_node):
            name = name_node.id
            if re.match(r'^[a-z]+[A-Z][a-zA-Z0-9]*$', name):
                s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
                suggested = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
                self.smells.append({
                    'type': 'PEP 8 Naming Violation',
                    'value': f"Variable '{name}' uses camelCase naming",
                    'line': name_node.lineno,
                    'suggestion': f"Rename variable '{name}' to snake_case (e.g., '{suggested}')."
                })

        for target in node.targets:
            for child in ast.walk(target):
                if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                    check_name(child)

        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name) and isinstance(node.target.ctx, ast.Store):
            name = node.target.id
            if re.match(r'^[a-z]+[A-Z][a-zA-Z0-9]*$', name):
                s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
                suggested = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
                self.smells.append({
                    'type': 'PEP 8 Naming Violation',
                    'value': f"Variable '{name}' uses camelCase naming",
                    'line': node.target.lineno,
                    'suggestion': f"Rename variable '{name}' to snake_case (e.g., '{suggested}')."
                })
        self.generic_visit(node)

    def visit_Subscript(self, node):
        # Check for raw zero array index
        if isinstance(node.slice, ast.Constant):
            val = node.slice.value
            if val == 0:
                self.smells.append({
                    'type': 'Raw Zero Array Index',
                    'value': "Index '0' used in array/dictionary lookup",
                    'line': node.lineno,
                    'suggestion': "Avoid using raw zero literal indices directly. Use unpacking, a named variable, or sequence slicing instead."
                })
        self.generic_visit(node)


def perform_code_analysis(code_input, ai_model='qwen-32b', refactor_level='balanced', smells_threshold='verbose'):
    """
    DETECTION CENTER: Identifies multiple types of code smells.
    """
    results = {
        'errors': [], 
        'oop_concepts': [], 
        'code_smells': [], 
        'refactoring_suggestions': []
    }

    # 1. Extract OOP and Syntax Errors
    results['oop_concepts'] = extract_oop_features(code_input)
    results['errors'] = detect_errors(code_input)
    results['code_smells'].extend(
        detect_oop_design_smells(code_input, results['oop_concepts'])
    )

    # 2. Manual AST Logic for Multiple Smell Types
    try:
        tree = ast.parse(code_input)
        complexity = 1

        for node in ast.walk(tree):
            # A. Calculate Complexity (Counts loops and conditionals)
            if isinstance(node, (ast.If, ast.For, ast.While, ast.And, ast.Or, ast.ExceptHandler)):
                complexity += 1

            # B. Detect Long Methods and Magic Numbers — checked PER FUNCTION, not whole file
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_loc = (node.end_lineno - node.lineno) + 1  # lines in this specific function
                # Threshold raised to 50 so beginners with many inline comments
                # are not penalised for writing well-annotated learning code.
                if func_loc > 50:
                    results['code_smells'].append({
                        'type': 'Long Method / God Function',
                        'value': f"'{node.name}()' is {func_loc} lines long (line {node.lineno})",
                        'line': node.lineno,
                        'suggestion': (
                            f"The function '{node.name}' is too long ({func_loc} lines). "
                            "Split it into multiple smaller, single-purpose methods."
                        )
                    })

                # First, collect every Constant that lives inside a Subscript
                # (slice index like [-4:] or [0:10]) — these are NOT magic numbers.
                slice_constant_ids: set = set()
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Subscript):
                        for slice_child in ast.walk(sub.slice):
                            # Plain constant:  [4:]
                            if isinstance(slice_child, ast.Constant):
                                slice_constant_ids.add(id(slice_child))
                            # Negated constant: [-4:]  →  UnaryOp(USub, Constant(4))
                            if isinstance(slice_child, ast.UnaryOp) and isinstance(slice_child.op, ast.USub):
                                for operand in ast.walk(slice_child.operand):
                                    if isinstance(operand, ast.Constant):
                                        slice_constant_ids.add(id(operand))

                # Now flag magic numbers, skipping any slice-resident constants
                for sub in ast.walk(node):
                    if (
                        isinstance(sub, ast.Constant)
                        and isinstance(sub.value, (int, float))
                        and sub.value not in (0, 1, -1)
                        and id(sub) not in slice_constant_ids   # ← skip slice indices
                    ):
                        results['code_smells'].append({
                            'type': 'Magic Number',
                            'value': f"Literal value '{sub.value}'",
                            'line': sub.lineno,
                            'suggestion': 'Extract this number to a named constant (e.g., MAX_RETRIES = 5).'
                        })

        # C. Identify 'Spaghetti Code' (Complexity Threshold)
        if complexity > 6:
            results['code_smells'].append({
                'type': 'High Cyclomatic Complexity',
                'value': f"Complexity Score: {complexity}",
                'suggestion': 'This code has too many nested branches. Break it into smaller functions.'
            })

        # D. Identify 'Procedural Design' (Missing OOP)
        # Only shown in verbose mode — beginners writing flat procedural scripts
        # should not be pushed toward OOP before they are ready.
        if smells_threshold == 'verbose' and not results['oop_concepts']:
            results['code_smells'].append({
                'type': 'Procedural Structure',
                'value': '0 Classes Detected',
                'suggestion': 'Consider using a Class structure to better manage data state and logic.'
            })

        if smells_threshold == 'verbose':
            visitor = VerboseSmellsVisitor()
            visitor.visit(tree)
            results['code_smells'].extend(visitor.smells)

    except SyntaxError:
        pass

    # 4. Severity Threshold Filtering of detected smells
    if smells_threshold == 'warnings':
        # Excludes minor smells (like Magic Number)
        results['code_smells'] = [
            s for s in results['code_smells'] 
            if s.get('type') != 'Magic Number'
        ]
    elif smells_threshold == 'strict':
        # Excludes all minor/styling smells and only retains critical layout/architectural errors:
        # High Cyclomatic Complexity, Procedural Structure, Feature Envy / Tight Coupling, and Long Method / God Function.
        critical_smells = {
            'High Cyclomatic Complexity',
            'Procedural Structure',
            'Feature Envy / Tight Coupling',
            'Long Method / God Function'
        }
        results['code_smells'] = [
            s for s in results['code_smells']
            if s.get('type') in critical_smells
        ]

    # 3. AI SURGEON INJECTION (Always provide a refactored version if smells exist)
    if results['code_smells'] or not results['oop_concepts']:
        fixed_code = generate_refactored_code(code_input, ai_model=ai_model, refactor_level=refactor_level)
        results['refactoring_suggestions'].append({
            'priority': 'high',
            'suggestion': 'The AI Surgeon has optimized the structural logic of your code.',
            'refactored_code': fixed_code
        })

    return results

@login_required(login_url='login')
def functionalities(request):
    analysis_id = request.GET.get('id')
    source = request.GET.get('source')
    analysis = CodeAnalysis.objects.get(id=analysis_id, user=request.user)

    errors = analysis.errors_detected.all()
    oop_concepts = analysis.oop_concepts.all()
    code_smells = analysis.code_smells.all()
    refactoring_suggestions = analysis.refactoring_suggestions.all()

    error_count = errors.count()
    smell_count = code_smells.count()
    oop_count = oop_concepts.count()
    refactor_count = refactoring_suggestions.exclude(refactored_code='').exclude(refactored_code__isnull=True).count()

    health_score = max(12, min(100, 100 - (error_count * 14) - (smell_count * 7)))
    if health_score >= 85:
        health_label = 'Excellent'
    elif health_score >= 65:
        health_label = 'Good'
    elif health_score >= 45:
        health_label = 'Fair'
    else:
        health_label = 'Needs work'

    context = {
        'analysis': analysis,
        'errors': errors,
        'oop_concepts': oop_concepts,
        'code_smells': code_smells,
        'refactoring_suggestions': refactoring_suggestions,
        'source': source,
        'error_count': error_count,
        'smell_count': smell_count,
        'oop_count': oop_count,
        'refactor_count': refactor_count,
        'health_score': health_score,
        'health_label': health_label,
    }
    return render(request, 'functionalities.html', context)

# (Keeping your other standard functions get_analysis_detail, history, delete, star, etc. same)
def _health_from_counts(error_count, smell_count):
    health_score = max(12, min(100, 100 - (error_count * 14) - (smell_count * 7)))
    if health_score >= 85:
        health_label = 'Excellent'
    elif health_score >= 65:
        health_label = 'Good'
    elif health_score >= 45:
        health_label = 'Fair'
    else:
        health_label = 'Needs work'
    return health_score, health_label


def _analysis_health(analysis):
    error_count = analysis.errors_detected.count()
    smell_count = analysis.code_smells.count()
    health_score, health_label = _health_from_counts(error_count, smell_count)
    return error_count, smell_count, health_score, health_label


def _history_meta(analysis):
    history_entry = getattr(analysis, 'history_entry', None)
    if not history_entry:
        return '', False, None
    title = history_entry.title or f'Analysis #{analysis.id}'
    return title, history_entry.is_starred, history_entry.created_at.isoformat()


_CODE_PREVIEW_LEN = 1200
_SUMMARY_ERROR_LIMIT = 6
_SUMMARY_SMELL_LIMIT = 6


def _bulk_limited_errors(analysis_ids):
    grouped = {aid: [] for aid in analysis_ids}
    if not analysis_ids:
        return grouped
    for row in (
        AnalysisError.objects.filter(analysis_id__in=analysis_ids)
        .order_by('analysis_id', 'id')
        .values('analysis_id', 'error_type', 'message', 'line_number')
    ):
        bucket = grouped[row['analysis_id']]
        if len(bucket) < _SUMMARY_ERROR_LIMIT:
            bucket.append({
                'error_type': row['error_type'],
                'message': row['message'],
                'line_number': row['line_number'],
            })
    return grouped


def _bulk_limited_smells(analysis_ids):
    grouped = {aid: [] for aid in analysis_ids}
    if not analysis_ids:
        return grouped
    for row in (
        CodeSmell.objects.filter(analysis_id__in=analysis_ids)
        .order_by('analysis_id', 'id')
        .values('analysis_id', 'smell_type')
    ):
        bucket = grouped[row['analysis_id']]
        if len(bucket) < _SUMMARY_SMELL_LIMIT:
            bucket.append({'smell_type': row['smell_type']})
    return grouped


def _preview_payload(analysis_id, history_row, error_count, smell_count, errors, code_smells, code_input=''):
    health_score, health_label = _health_from_counts(error_count, smell_count)
    title = history_row.title or f'Analysis #{analysis_id}'
    return {
        'id': analysis_id,
        'summary': True,
        'title': title,
        'is_starred': history_row.is_starred,
        'created_at': history_row.created_at.isoformat(),
        'error_count': error_count,
        'smell_count': smell_count,
        'health_score': health_score,
        'health_label': health_label,
        'errors': errors,
        'code_smells': code_smells,
        'code_input': code_input,
        'code_loaded': bool(code_input),
        'code_truncated': False,
        'errors_truncated': error_count > len(errors),
        'smells_truncated': smell_count > len(code_smells),
    }


def build_history_previews(user, history_rows):
    """Build preview JSON for all items on the current history page (few DB round-trips)."""
    if not history_rows:
        return {}
    analysis_ids = [h.analysis_id for h in history_rows]
    count_rows = {
        row['id']: row
        for row in CodeAnalysis.objects.filter(id__in=analysis_ids, user=user)
        .annotate(
            error_count=Count('errors_detected', distinct=True),
            smell_count=Count('code_smells', distinct=True),
        )
        .values('id', 'error_count', 'smell_count')
    }
    errors_by = _bulk_limited_errors(analysis_ids)
    smells_by = _bulk_limited_smells(analysis_ids)
    previews = {}
    for history_row in history_rows:
        aid = history_row.analysis_id
        counts = count_rows.get(aid, {'error_count': 0, 'smell_count': 0})
        previews[str(aid)] = _preview_payload(
            aid,
            history_row,
            counts['error_count'],
            counts['smell_count'],
            errors_by.get(aid, []),
            smells_by.get(aid, []),
        )
    return previews


def _code_preview_text(raw_code):
    raw_code = raw_code or ''
    code_truncated = len(raw_code) > _CODE_PREVIEW_LEN
    code_input = raw_code[:_CODE_PREVIEW_LEN]
    if code_truncated:
        code_input += '\n… (preview — open Full report for complete code)'
    return code_input, code_truncated


@login_required(login_url='login')
def get_analysis_detail(request, analysis_id):
    summary = request.GET.get('summary') == '1'

    if summary:
        try:
            analysis = (
                CodeAnalysis.objects.filter(id=analysis_id, user=request.user)
                .select_related('history_entry')
                .annotate(
                    error_count=Count('errors_detected', distinct=True),
                    smell_count=Count('code_smells', distinct=True),
                )
                .defer('code_input')
                .get()
            )
        except CodeAnalysis.DoesNotExist:
            return JsonResponse({'error': 'Analysis not found'}, status=404)

        try:
            errors = list(
                analysis.errors_detected.order_by('id').values(
                    'error_type', 'message', 'line_number'
                )[:_SUMMARY_ERROR_LIMIT]
            )
            code_smells = list(
                analysis.code_smells.order_by('id').values('smell_type')[
                    :_SUMMARY_SMELL_LIMIT
                ]
            )
            title, is_starred, created_at = _history_meta(analysis)
            health_score, health_label = _health_from_counts(
                analysis.error_count, analysis.smell_count
            )

            code_input = ''
            code_truncated = False
            if request.GET.get('include_code') == '1':
                raw_code = (
                    CodeAnalysis.objects.filter(pk=analysis_id, user=request.user)
                    .values_list('code_input', flat=True)
                    .first()
                )
                code_input, code_truncated = _code_preview_text(raw_code)

            return JsonResponse({
                'id': analysis.id,
                'summary': True,
                'title': title or f'Analysis #{analysis.id}',
                'is_starred': is_starred,
                'created_at': created_at,
                'error_count': analysis.error_count,
                'smell_count': analysis.smell_count,
                'health_score': health_score,
                'health_label': health_label,
                'errors': errors,
                'code_smells': code_smells,
                'code_input': code_input,
                'code_loaded': bool(code_input),
                'code_truncated': code_truncated,
                'errors_truncated': analysis.error_count > len(errors),
                'smells_truncated': analysis.smell_count > len(code_smells),
            })
        except Exception as exc:
            traceback.print_exc()
            return JsonResponse(
                {'error': f'Could not load preview: {exc}'},
                status=500,
            )

    try:
        analysis = (
            CodeAnalysis.objects.filter(id=analysis_id, user=request.user)
            .select_related('history_entry')
            .prefetch_related(
                'errors_detected', 'oop_concepts', 'code_smells', 'refactoring_suggestions'
            )
            .get()
        )
    except CodeAnalysis.DoesNotExist:
        return JsonResponse({'error': 'Analysis not found'}, status=404)

    errors_qs = list(analysis.errors_detected.all())
    smells_qs = list(analysis.code_smells.all())
    oop_qs = list(analysis.oop_concepts.all())
    refactor_qs = list(analysis.refactoring_suggestions.all())

    error_count = len(errors_qs)
    smell_count = len(smells_qs)
    oop_count = len(oop_qs)
    refactor_count = sum(1 for r in refactor_qs if r.refactored_code and r.refactored_code.strip())
    health_score, health_label = _health_from_counts(error_count, smell_count)
    title, is_starred, created_at = _history_meta(analysis)

    return JsonResponse({
        'id': analysis.id,
        'code_input': analysis.code_input,
        'title': title,
        'is_starred': is_starred,
        'created_at': created_at,
        'error_count': error_count,
        'smell_count': smell_count,
        'oop_count': oop_count,
        'refactor_count': refactor_count,
        'health_score': health_score,
        'health_label': health_label,
        'errors': [
            {'error_type': e.error_type, 'message': e.message, 'line_number': e.line_number}
            for e in errors_qs
        ],
        'oop_concepts': [
            {'concept_name': o.concept_name, 'details': o.details}
            for o in oop_qs
        ],
        'code_smells': [
            {
                'smell_type': s.smell_type,
                'detected_value': s.detected_value,
                'line_number': s.line_number,
                'suggestion': s.suggestion,
            }
            for s in smells_qs
        ],
        'refactoring_suggestions': [
            {
                'priority': r.priority,
                'suggestion_text': r.suggestion_text,
                'refactored_code': r.refactored_code,
            }
            for r in refactor_qs
        ],
    })
@login_required(login_url='login')
def history(request):
    from django.core.paginator import Paginator

    # Avoid pulling the full `CodeAnalysis.code_input` text for each history row —
    # deferring it prevents transferring large blobs and speeds up the list view.
    qs = AnalysisHistory.objects.filter(user=request.user, is_deleted=False).select_related('analysis').defer('analysis__code_input').order_by('-created_at')
    search = request.GET.get('search', '').strip()
    filter_type = request.GET.get('filter', 'all')

    if search:
        qs = qs.filter(title__icontains=search)
    if filter_type == 'starred':
        qs = qs.filter(is_starred=True)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    starred_count = AnalysisHistory.objects.filter(
        user=request.user, is_deleted=False, is_starred=True
    ).count()

    history_rows = list(page_obj.object_list)

    return render(request, 'history.html', {
        'page_obj': page_obj,
        'search': search,
        'filter_type': filter_type,
        'total_count': paginator.count,
        'starred_count': starred_count,
        'history_previews': build_history_previews(request.user, history_rows),
    })

@login_required(login_url='login')
def delete_history(request, history_id):
    history = AnalysisHistory.objects.get(id=history_id, user=request.user)
    history.is_deleted = True
    history.save()
    return JsonResponse({'success': True})

@login_required(login_url='login')
@require_http_methods(['POST'])
def clear_all_history(request):
    """Soft-delete every history entry belonging to the current user."""
    count = AnalysisHistory.objects.filter(
        user=request.user, is_deleted=False
    ).update(is_deleted=True)
    return JsonResponse({'success': True, 'cleared': count})

@login_required(login_url='login')
def star_analysis(request, analysis_id):
    history = AnalysisHistory.objects.get(analysis_id=analysis_id, user=request.user)
    history.is_starred = not history.is_starred
    history.save()
    return JsonResponse({'success': True, 'is_starred': history.is_starred})
@login_required(login_url='login')
@require_http_methods(["POST"])
def ai_explain(request):
    """A universal AI Tutor that explains Errors, Code Smells, and OOP Concepts."""
    try:
        data = json.loads(request.body)
        context_type = data.get('context_type', 'Error')
        item_title = data.get('item_title', '')
        item_details = data.get('item_details', '')
        if context_type == 'Code Smell':
            prompt = f"Explain this Code Smell to a beginner. Why is it considered bad practice, and how does fixing it help?\nSmell: {item_title}\nDetails: {item_details}"
        elif context_type == 'OOP Concept':
            prompt = f"Explain this Object-Oriented Programming (OOP) concept to a beginner using a simple real-world analogy. Keep it easy to understand.\nConcept: {item_title}\nDetails: {item_details}"
        elif context_type == 'Refactoring':
            prompt = f"Look at this refactored Python code. Explain to a beginner what clean code principles, design patterns, or optimizations were used here, and why this is better than messy procedural code.\nRefactored Code:\n{item_details}"
        else:
            prompt = f"Explain this Python error in simple terms for a beginner, and provide a short example of how to fix it.\nError Type: {item_title}\nMessage: {item_details}"

        payload = {
            "model": "Qwen/Qwen2.5-Coder-32B-Instruct",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful Python programming tutor. Keep explanations concise, clear, and beginner-friendly. Output using basic HTML tags (like <b>, <br>, <pre> for code) so it looks good on a webpage. Do not use Markdown."
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 350
        }

        response = requests.post(API_URL, headers=headers, json=payload)

        if response.status_code == 200:
            result = response.json()
            explanation = result['choices'][0]['message']['content'].strip()
            return JsonResponse({'success': True, 'explanation': explanation})
        else:
            return JsonResponse({'success': False, 'error': f"API Error {response.status_code}"})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
   
@login_required(login_url='login')
def dashboard(request):
    """Generates user statistics for the Analytics Dashboard."""
    
    # 1. Top Errors
    top_errors = AnalysisError.objects.filter(analysis__user=request.user) \
        .values('error_type') \
        .annotate(count=Count('id')) \
        .order_by('-count')[:5]
        
    # 2. Top Code Smells
    top_smells = CodeSmell.objects.filter(analysis__user=request.user) \
        .values('smell_type') \
        .annotate(count=Count('id')) \
        .order_by('-count')[:5]
        
    # 3. Activity Trend (Last 7 Days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    activity = CodeAnalysis.objects.filter(user=request.user, created_at__gte=seven_days_ago) \
        .annotate(date=TruncDate('created_at')) \
        .values('date') \
        .annotate(count=Count('id')) \
        .order_by('date')
        
    # Format dates for JSON serialization in the template
    activity_data = [{'date': item['date'].strftime('%b %d'), 'count': item['count']} for item in activity]
    
    context = {
        # json.dumps allows us to pass Python lists directly into JavaScript!
        'top_errors_json': json.dumps(list(top_errors)),
        'top_smells_json': json.dumps(list(top_smells)),
        'activity_json': json.dumps(activity_data),
        'total_analyses': request.user.analyses.count()
    }
    
    return render(request, 'dashboard.html', context)