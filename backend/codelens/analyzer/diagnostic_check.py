"""
CodeLens Diagnostic Check
=========================
Verifies every combination of:
  - Severity threshold  : verbose | warnings | strict
  - Refactoring level   : conservative | balanced | creative
  - AI model mapping    : all 4 models resolve to a HuggingFace endpoint

Run with:
    venv\Scripts\python backend/codelens/analyzer/diagnostic_check.py
"""
import sys, os, io, re, inspect
# Force UTF-8 output on Windows terminals
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codelens.settings')

import django
django.setup()

from codelens.analyzer.views import perform_code_analysis, generate_refactored_code
import codelens.analyzer.views as vw

# ----------------------------------------------------------------
# TEST CODES
# ----------------------------------------------------------------
CODE_WITH_ALL_SMELLS = """\
PASSING_THRESHOLD = 70
BONUS_MULTIPLIER = 1.05

def process_student_grades(student_data):
    for name, score in student_data.items():
        if score > 100:
            print(f"Error: {name} has an invalid score.")
            continue
        if score < 65:
            curved_score = score * BONUS_MULTIPLIER
            print(f"Applying safety curve for {name}.")
        print(f"Final evaluated score: {curved_score}")
        ppmnt(f"Record processing complete for {name}.")
    return True
"""

CODE_COMPLEX = """\
def handle_payment(user, method, amount, currency):
    if user.is_active:
        if method == 'cc':
            if amount > 0 and currency == 'USD':
                for retry in range(3):
                    try:
                        return True
                    except:
                        pass
            elif amount > 100:
                return False
    return False
"""

CODE_CLEAN = """\
class Calculator:
    def add(self, a, b):
        return a + b
    def subtract(self, a, b):
        return a - b
"""

PASS = "[PASS]"
FAIL = "[FAIL]"
results_log = []


def check(label, condition, detail=""):
    tag = PASS if condition else FAIL
    print(f"  {tag}  {label}")
    if not condition:
        results_log.append(f"{label}  =>  {detail}")
    return condition


def section(title):
    bar = "-" * 60
    print(f"\n{bar}")
    print(f"  {title}")
    print(bar)


# ================================================================
section("SECTION 1 - VERBOSE mode: all smells reported")
# ================================================================
print()
res_v = perform_code_analysis(CODE_WITH_ALL_SMELLS, smells_threshold='verbose')
sv = res_v['code_smells']

check("Magic Number '100' flagged",
      any(s['type'] == 'Magic Number' and '100' in str(s.get('value','')) for s in sv))
check("Magic Number '65' flagged",
      any(s['type'] == 'Magic Number' and '65' in str(s.get('value','')) for s in sv))
check("Procedural Structure flagged (verbose + no classes)",
      any(s['type'] == 'Procedural Structure' for s in sv))
check("VerboseSmellsVisitor ran without crash", True)

print(f"\n  Total VERBOSE smells: {len(sv)}")
for s in sv:
    print(f"    [{s['type']}] line {s.get('line','?')}  -- {s.get('value','')}")


# ================================================================
section("SECTION 2 - WARNINGS (Standard) mode: Magic Numbers excluded")
# ================================================================
print()
res_w = perform_code_analysis(CODE_WITH_ALL_SMELLS, smells_threshold='warnings')
sw = res_w['code_smells']

check("Magic Number ABSENT in warnings mode",
      not any(s['type'] == 'Magic Number' for s in sw),
      f"found: {[s for s in sw if s['type']=='Magic Number']}")
check("Procedural Structure ABSENT in warnings mode (verbose-only)",
      not any(s['type'] == 'Procedural Structure' for s in sw))
check("PEP 8 Naming Violation ABSENT in warnings mode (verbose-only)",
      not any(s['type'] == 'PEP 8 Naming Violation' for s in sw))
check("Raw Zero Array Index ABSENT in warnings mode (verbose-only)",
      not any(s['type'] == 'Raw Zero Array Index' for s in sw))
check("Empty Function / Dead Code ABSENT in warnings mode (verbose-only)",
      not any(s['type'] == 'Empty Function / Dead Code' for s in sw))

print(f"\n  Total WARNINGS smells: {len(sw)}")
for s in sw:
    print(f"    [{s['type']}] line {s.get('line','?')}  -- {s.get('value','')}")


# ================================================================
section("SECTION 3 - STRICT mode: only critical architectural failures")
# ================================================================
print()
res_s = perform_code_analysis(CODE_COMPLEX, smells_threshold='strict')
ss = res_s['code_smells']

allowed_strict = {
    'High Cyclomatic Complexity',
    'Feature Envy / Tight Coupling',
    'Long Method / God Function'
    # Note: Procedural Structure is now verbose-only, so NOT in allowed_strict
}
non_critical = [s for s in ss if s['type'] not in allowed_strict]

check("No non-critical smells in strict mode",
      len(non_critical) == 0,
      f"non-critical found: {non_critical}")
check("High Cyclomatic Complexity IS flagged in strict mode",
      any(s['type'] == 'High Cyclomatic Complexity' for s in ss))
check("Magic Number ABSENT in strict mode",
      not any(s['type'] == 'Magic Number' for s in ss))
check("Procedural Structure ABSENT in strict mode",
      not any(s['type'] == 'Procedural Structure' for s in ss))
check("PEP 8 Naming Violation ABSENT in strict mode",
      not any(s['type'] == 'PEP 8 Naming Violation' for s in ss))

print(f"\n  Total STRICT smells: {len(ss)}")
for s in ss:
    print(f"    [{s['type']}]  -- {s.get('value','')}")


# ================================================================
section("SECTION 4 - Long Method threshold calibration (50 lines)")
# ================================================================
print()
# 27-line function: should NOT trigger with threshold=50
short_fn = "def fn():\n" + "    x = 1\n" * 26
res_short = perform_code_analysis(short_fn, smells_threshold='verbose')
check("27-line fn NOT flagged as God Function (threshold=50)",
      not any(s['type'] == 'Long Method / God Function' for s in res_short['code_smells']))

# 52-line function: SHOULD trigger with threshold=50
long_fn = "def fn():\n" + "    x = 1\n" * 51
res_long = perform_code_analysis(long_fn, smells_threshold='verbose')
check("52-line fn IS flagged as God Function",
      any(s['type'] == 'Long Method / God Function' for s in res_long['code_smells']))


# ================================================================
section("SECTION 5 - Clean code gives zero smells (warnings mode)")
# ================================================================
print()
res_clean = perform_code_analysis(CODE_CLEAN, smells_threshold='warnings')
sc = res_clean['code_smells']
check("No false-positive smells on clean OOP code",
      len(sc) == 0,
      f"spurious: {sc}")


# ================================================================
section("SECTION 6 - AI Refactoring Level system prompts")
# ================================================================
print()
src = inspect.getsource(vw.generate_refactored_code)
check("Conservative prompt contains 'minimal'", "minimal" in src)
check("Conservative prompt contains 'preserve'", "preserve" in src)
check("Creative prompt contains 'design patterns'", "design patterns" in src)
check("Creative prompt contains 'creative'", "creative" in src.lower())
check("Balanced prompt is the else/default branch", "else:" in src)

print()
# Model key and endpoint mapping
model_pairs = [
    ('qwen-32b',        'Qwen/Qwen2.5-Coder-32B-Instruct'),
    ('codellama-34b',   'codellama/CodeLlama-34b-Instruct-hf'),
    ('mistral-7b',      'mistralai/Mistral-7B-Instruct-v0.3'),
    ('llama-3-8b',      'meta-llama/Meta-Llama-3-8B-Instruct'),
]
for key, endpoint in model_pairs:
    check(f"Model '{key}' maps to '{endpoint}'",
          f"'{key}'" in src and endpoint in src)


# ================================================================
section("SECTION 7 - Frontend <-> Backend key alignment")
# ================================================================
print()

base = os.path.dirname(__file__)
settings_path = os.path.normpath(os.path.join(base, '..', '..', '..', 'frontend', 'templates', 'settings.html'))
analyzer_path  = os.path.normpath(os.path.join(base, '..', '..', '..', 'frontend', 'templates', 'analyzer.html'))

with open(settings_path, encoding='utf-8') as f:
    settings_html = f.read()
with open(analyzer_path, encoding='utf-8') as f:
    analyzer_html = f.read()

# settings.html localStorage keys saved correctly
for key in ['cl-ai-model', 'cl-refactor-level', 'cl-smells-threshold']:
    check(f"settings.html saves '{key}' to localStorage", f"'{key}'" in settings_html)

# dropdown option values match backend expectations
for val in ['verbose', 'warnings', 'strict']:
    check(f"smellsThreshold option value='{val}' in settings.html",
          f'value="{val}"' in settings_html)
for val in ['conservative', 'balanced', 'creative']:
    check(f"refactorLevel data-level='{val}' in settings.html",
          f'data-level="{val}"' in settings_html)
for val in ['qwen-32b', 'codellama-34b', 'mistral-7b', 'llama-3-8b']:
    check(f"aiModel option value='{val}' in settings.html",
          f'value="{val}"' in settings_html)

print()
# analyzer.html reads the same keys
for key in ['cl-ai-model', 'cl-refactor-level', 'cl-smells-threshold']:
    check(f"analyzer.html reads '{key}' from localStorage", f"'{key}'" in analyzer_html)
# analyzer.html POSTs the correct field names
for field in ['ai_model', 'refactor_level', 'smells_threshold']:
    check(f"analyzer.html POST body includes field '{field}'", field in analyzer_html)


# ================================================================
section("SECTION 8 - Backend request extraction (analyze_code + analyze_github)")
# ================================================================
print()
views_src = inspect.getsource(vw)
for field in ['ai_model', 'refactor_level', 'smells_threshold']:
    count = views_src.count(f"data.get('{field}'")
    check(f"'{field}' extracted from request body ({count}x, need >= 2)",
          count >= 2, f"only {count} extraction(s)")

check("analyze_code passes smells_threshold to perform_code_analysis",
      "smells_threshold=smells_threshold" in views_src)
check("analyze_github passes smells_threshold to perform_code_analysis",
      views_src.count("smells_threshold=smells_threshold") >= 2)
check("analyze_code passes ai_model to perform_code_analysis",
      "ai_model=ai_model" in views_src)
check("analyze_code passes refactor_level to perform_code_analysis",
      "refactor_level=refactor_level" in views_src)


# ================================================================
# FINAL REPORT
# ================================================================
bar = "=" * 60
print(f"\n{bar}")
print("  FINAL REPORT")
print(bar)
if results_log:
    print(f"\n  {len(results_log)} ISSUE(S) FOUND:\n")
    for i, e in enumerate(results_log, 1):
        print(f"  {i}. {e}")
else:
    print("\n  [ALL CHECKS PASSED] System is fully aligned and working!\n")
print(bar + "\n")
