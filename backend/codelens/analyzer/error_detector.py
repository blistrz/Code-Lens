import ast
import builtins

# --- 1. HEALTH INSPECTOR ---
class ErrorDetectorVisitor(ast.NodeVisitor):
    def __init__(self):
        initial_scope = set(dir(builtins))
        magic_variables = {
            '__file__', '__name__', '__doc__', '__package__', 
            '__loader__', '__spec__', '__annotations__',
            'ast', 'builtins' 
        }
        self.scope_stack = [initial_scope | magic_variables]
        self.errors = []

    def _is_defined(self, name):
        for scope in reversed(self.scope_stack):
            if name in scope:
                return True
        return False

    def _add_to_current_scope(self, name):
        self.scope_stack[-1].add(name)

    def _add_targets_to_scope(self, target_node):
        for child in ast.walk(target_node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                self._add_to_current_scope(child.id)

    def visit_ClassDef(self, node):
        self._add_to_current_scope(node.name)
        self.scope_stack.append(set())
        self.generic_visit(node)
        self.scope_stack.pop() 

    def visit_FunctionDef(self, node):
        self._add_to_current_scope(node.name)
        self.scope_stack.append(set())
        for arg in node.args.args:
            self._add_to_current_scope(arg.arg)
        # Also handle *args, **kwargs, keyword-only args, and defaults
        if node.args.vararg:
            self._add_to_current_scope(node.args.vararg.arg)
        if node.args.kwarg:
            self._add_to_current_scope(node.args.kwarg.arg)
        for arg in node.args.kwonlyargs:
            self._add_to_current_scope(arg.arg)
        self.generic_visit(node)
        self.scope_stack.pop()

    # Alias for async functions
    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Import(self, node):
        """Register 'import X' and 'import X as Y' names into the current scope."""
        for alias in node.names:
            # Use the alias if present (e.g. 'import numpy as np' → 'np'),
            # otherwise use the top-level module name (e.g. 'import os.path' → 'os').
            bound_name = alias.asname if alias.asname else alias.name.split('.')[0]
            self._add_to_current_scope(bound_name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Register 'from X import Y' and 'from X import Y as Z' names into the current scope."""
        for alias in node.names:
            bound_name = alias.asname if alias.asname else alias.name
            # 'from module import *' — we can't know the names statically;
            # add a sentinel so the scope is considered 'open' (we skip this case).
            if bound_name != '*':
                self._add_to_current_scope(bound_name)
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            if not self._is_defined(node.id):
                self.errors.append({
                    'type': 'UndefinedVariable',
                    'message': f"Variable '{node.id}' used before definition",
                    'line': getattr(node, 'lineno', None),
                    'suggestion': f"Define '{node.id}' in the current or global scope"
                })
        self.generic_visit(node)

    def visit_BinOp(self, node):
        if isinstance(node.op, ast.Div):
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                self.errors.append({
                    'type': 'RuntimeError',
                    'message': 'Division by zero detected',
                    'line': getattr(node, 'lineno', None),
                    'suggestion': 'Check denominator before division'
                })
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            self._add_targets_to_scope(target)
        self.generic_visit(node)

    def visit_For(self, node):
        self._add_targets_to_scope(node.target)
        self.generic_visit(node)

    def visit_ListComp(self, node):
        self.scope_stack.append(set())
        for generator in node.generators:
            self._add_targets_to_scope(generator.target)
        self.generic_visit(node)
        self.scope_stack.pop()


# --- 2. THE ARCHITECT ---
class OOPDetector(ast.NodeVisitor):
    def __init__(self):
        self.classes = []

    def visit_ClassDef(self, node):
        methods = []
        for item in node.body:
            # Capture both regular and async method definitions
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                is_async = isinstance(item, ast.AsyncFunctionDef)
                methods.append({
                    'name': item.name,
                    'type': self._classify_method(item.name, is_async=is_async),
                    'line': item.lineno
                })

        self.classes.append({
            'name': node.name,
            'line': node.lineno,
            'bases': [self._get_base_name(b) for b in node.bases],
            'methods': methods,
            'method_count': len(methods)
        })
        self.generic_visit(node)

    def _classify_method(self, name, is_async: bool = False):
        prefix = "Async / " if is_async else ""
        if name.startswith('__') and name.endswith('__'): return f"{prefix}Special (Dunder)"
        if name.startswith('__'): return f"{prefix}Private"
        if name.startswith('_'): return f"{prefix}Protected"
        return f"{prefix}Public"

    def _get_base_name(self, node):
        if isinstance(node, ast.Name): return node.id
        if isinstance(node, ast.Attribute): return f"{self._get_base_name(node.value)}.{node.attr}"
        return "Unknown"


# --- 3. MAIN WRAPPER FUNCTIONS ---
def detect_errors(code):
    try:
        tree = ast.parse(code)
        visitor = ErrorDetectorVisitor()
        visitor.visit(tree)
        return visitor.errors
    except SyntaxError as e:
        return [{
            'type': 'SyntaxError',
            'message': str(e),
            'line': e.lineno,
            'suggestion': 'Check Python syntax, indentation, and colons.'
        }]
    except Exception as e:
        return [{'type': 'SystemError', 'message': str(e)}]


def _is_pep8_class_name(name):
    """PEP 8: classes use CapWords (PascalCase), not snake_case."""
    if not name or not name[0].isupper():
        return False
    if '_' in name:
        return False
    if name.isupper() and len(name) > 1:
        return False
    return True


def _snake_to_pascal(name):
    return ''.join(part.capitalize() for part in name.split('_') if part)


def _detect_feature_envy(tree):
    """Flag methods that reach into another object's attributes (tight coupling)."""
    issues = []
    for class_node in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        for item in class_node.body:
            if not isinstance(item, ast.FunctionDef):
                continue
            if item.name == '__init__':
                continue
            param_names = [arg.arg for arg in item.args.args[1:]]
            if not param_names:
                continue
            external_attrs = {p: set() for p in param_names}
            for node in ast.walk(item):
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                    if node.value.id in external_attrs:
                        external_attrs[node.value.id].add(node.attr)
            for param, attrs in external_attrs.items():
                if not attrs:
                    continue
                sensitive = {'users', 'data', 'items', 'records', 'accounts', 'entries'}
                if len(attrs) >= 2 or attrs & sensitive:
                    issues.append({
                        'class': class_node.name,
                        'method': item.name,
                        'param': param,
                        'attrs': sorted(attrs),
                        'line': item.lineno,
                    })
    return issues


def detect_oop_design_smells(code, classes=None):
    """PEP 8 naming + Feature Envy / tight coupling between classes."""
    if classes is None:
        classes = extract_oop_features(code)
    smells = []
    class_names = {c['name'] for c in classes}

    for cls in classes:
        name = cls['name']
        if not _is_pep8_class_name(name):
            suggested = _snake_to_pascal(name) if '_' in name else name
            smells.append({
                'type': 'Invalid Class Naming (PEP 8)',
                'value': f"Class '{name}'",
                'line': cls.get('line'),
                'class_name': name,
                'suggestion': (
                    f"Rename '{name}' to '{suggested}'. "
                    "Python classes should use PascalCase (CapWords), not snake_case."
                ),
            })

    try:
        tree = ast.parse(code)
        for issue in _detect_feature_envy(tree):
            attrs_text = ', '.join(issue['attrs'])
            other = issue['param']
            matched_class = next(
                (cn for cn in class_names if cn.lower() == other.lower()
                 or other.lower() in cn.lower() or cn.lower() in other.lower()),
                other,
            )
            smells.append({
                'type': 'Feature Envy / Tight Coupling',
                'value': (
                    f"{issue['class']}.{issue['method']}() → '{issue['param']}' "
                    f"({attrs_text})"
                ),
                'line': issue['line'],
                'class_name': issue['class'],
                'suggestion': (
                    f"The '{issue['class']}' class relies heavily on '{issue['param']}' "
                    f"internal data ({attrs_text}). This is tight coupling / Feature Envy — "
                    f"consider moving '{issue['method']}' onto '{matched_class}' or passing "
                    "only the specific data needed instead of the whole object."
                ),
            })
    except SyntaxError:
        pass

    return smells


def extract_oop_features(code):
    try:
        tree = ast.parse(code)
        detector = OOPDetector()
        detector.visit(tree)
        return detector.classes
    except Exception:
        return []