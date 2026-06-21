import unittest
from django.test import TestCase
from .error_detector import detect_errors, extract_oop_features, detect_oop_design_smells
from .views import perform_code_analysis

class CodeLensAnalyzerTests(TestCase):
    """
    Test suite for CodeLens static analysis visitors, scope tracking,
    and rule verification engine.
    """

    def test_syntax_and_division_by_zero(self):
        # 1. Valid syntax, no division by zero
        code_valid = "x = 10 / 2"
        errors = detect_errors(code_valid)
        self.assertEqual(len(errors), 0)

        # 2. Division by zero literal
        code_div_zero = "x = 10 / 0"
        errors = detect_errors(code_div_zero)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['type'], 'RuntimeError')
        self.assertIn("Division by zero detected", errors[0]['message'])

        # 3. Invalid python syntax
        code_syntax_err = "class PaymentMethod"
        errors = detect_errors(code_syntax_err)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['type'], 'SyntaxError')

    def test_undefined_variables_and_scoping(self):
        # 1. Global / Builtin variable usage (no error)
        code_ok = "print(len([1, 2, 3]))"
        errors = detect_errors(code_ok)
        self.assertEqual(len(errors), 0)

        # 2. Undefined variable lookup
        code_err = "x = undefined_variable + 10"
        errors = detect_errors(code_err)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['type'], 'UndefinedVariable')
        self.assertEqual(errors[0]['line'], 1)

        # 3. Local variable within function scope (no error)
        code_func = (
            "def calculate(value):\n"
            "    local_var = value * 2\n"
            "    return local_var\n"
        )
        errors = detect_errors(code_func)
        self.assertEqual(len(errors), 0)

        # 4. Import / Aliased import resolution (no error)
        code_import = (
            "import collections as col\n"
            "from typing import List, Dict\n"
            "x = col.deque()\n"
            "def get_list() -> List:\n"
            "    return []\n"
        )
        errors = detect_errors(code_import)
        self.assertEqual(len(errors), 0)

        # 5. List comprehension generator scoping (no leak / error)
        code_comp = (
            "items = [1, 2, 3]\n"
            "squares = [x * x for x in items]\n"
            "y = squares[0]\n"
        )
        errors = detect_errors(code_comp)
        self.assertEqual(len(errors), 0)

    def test_oop_feature_extraction(self):
        code_oop = (
            "class PaymentGateway:\n"
            "    def __init__(self, token):\n"
            "        self._token = token\n"
            "    def _validate(self):\n"
            "        pass\n"
            "    def __encrypt_details(self):\n"
            "        pass\n"
            "    async def process_async(self, amount):\n"
            "        pass\n"
            "    def execute_payment(self):\n"
            "        pass\n"
        )
        classes = extract_oop_features(code_oop)
        self.assertEqual(len(classes), 1)
        
        cls = classes[0]
        self.assertEqual(cls['name'], 'PaymentGateway')
        self.assertEqual(cls['method_count'], 5)

        methods = {m['name']: m['type'] for m in cls['methods']}
        self.assertEqual(methods['__init__'], 'Special (Dunder)')
        self.assertEqual(methods['_validate'], 'Protected')
        self.assertEqual(methods['__encrypt_details'], 'Private')
        self.assertEqual(methods['process_async'], 'Async / Public')
        self.assertEqual(methods['execute_payment'], 'Public')

    def test_oop_design_smells(self):
        # 1. Invalid Class Naming (PEP 8 camelcase check)
        code_invalid_name = "class payment_processor:\n    pass"
        smells = detect_oop_design_smells(code_invalid_name)
        self.assertTrue(any("PEP 8" in s['type'] for s in smells))

        # 2. Tight Coupling / Feature Envy check
        code_envy = (
            "class UserRecord:\n"
            "    def __init__(self):\n"
            "        self.username = ''\n"
            "        self.email = ''\n"
            "\n"
            "class Logger:\n"
            "    def log_user(self, record):\n"
            "        name = record.username\n"
            "        email = record.email\n"
            "        print(name, email)\n"
        )
        smells = detect_oop_design_smells(code_envy)
        self.assertTrue(any("Feature Envy" in s['type'] for s in smells))

    def test_string_slice_magic_number_filtering(self):
        # Slice indexing (like [-4:] or [2:10:2]) should NOT trigger Magic Number smells
        code_slice = (
            "class CardPayment:\n"
            "    def __init__(self, number):\n"
            "        self.number = number\n"
            "    def get_masked(self):\n"
            "        return f'****-****-****-{self.number[-4:]}'\n"
        )
        analysis_res = perform_code_analysis(code_slice)
        smells = analysis_res['code_smells']
        
        # Verify that constant 4 in self.number[-4:] is NOT flagged as a magic number
        magic_numbers = [s for s in smells if s['type'] == 'Magic Number']
        self.assertEqual(len(magic_numbers), 0)

        # Confirm that other standard magic numbers (outside slices) ARE flagged
        code_with_magic = (
            "def calculate_tax(amount):\n"
            "    if amount > 1000:\n"
            "        return amount * 0.15\n"
            "    return amount * 0.05\n"
        )
        analysis_res_magic = perform_code_analysis(code_with_magic)
        smells_magic = analysis_res_magic['code_smells']
        magic_numbers_detected = [s for s in smells_magic if s['type'] == 'Magic Number']
        self.assertTrue(len(magic_numbers_detected) >= 2)

    def test_high_cyclomatic_complexity(self):
        code_spaghetti = (
            "def handle_payment(user, method, amount, currency):\n"
            "    if user.is_active:\n"
            "        if method == 'cc':\n"
            "            if amount > 0 and currency == 'USD':\n"
            "                for retry in range(3):\n"
            "                    try:\n"
            "                        return True\n"
            "                    except:\n"
            "                        pass\n"
            "            elif amount > 100:\n"
            "                return False\n"
            "    return False\n"
        )
        analysis_res = perform_code_analysis(code_spaghetti)
        smells = analysis_res['code_smells']
        self.assertTrue(any("Complexity" in s['type'] for s in smells))

    def test_code_smells_severity_thresholds(self):
        code_input = (
            "def process_data(value):\n"
            "    if value > 100:\n"
            "        return value * 1000\n"
            "    return value\n"
        )
        
        # 1. Verbose: Magic numbers should be returned
        res_verbose = perform_code_analysis(code_input, smells_threshold='verbose')
        self.assertTrue(any(s['type'] == 'Magic Number' for s in res_verbose['code_smells']))

        # 2. Warnings: Magic numbers should be excluded
        res_warnings = perform_code_analysis(code_input, smells_threshold='warnings')
        self.assertFalse(any(s['type'] == 'Magic Number' for s in res_warnings['code_smells']))

        # 3. Strict: Only structural/design blockages should be returned, minor smells omitted.
        #    Procedural Structure is now verbose-only, so it must NOT appear here.
        res_strict = perform_code_analysis(code_input, smells_threshold='strict')
        self.assertFalse(any(s['type'] == 'Magic Number' for s in res_strict['code_smells']))
        self.assertFalse(any(s['type'] == 'Procedural Structure' for s in res_strict['code_smells']))

        # Verbose mode must still report Procedural Structure on code with no classes
        res_verbose_proc = perform_code_analysis(code_input, smells_threshold='verbose')
        self.assertTrue(any(s['type'] == 'Procedural Structure' for s in res_verbose_proc['code_smells']))

    def test_verbose_extra_smells(self):
        code_extra = (
            "DATABASE_PORT = 5432\n"
            "class MyProcessor:\n"
            "    def process(self, records):\n"
            "        user_records = records\n"
            "        first_val = user_records[0]\n"
            "        userScore = 95\n"
            "        return userScore\n"
            "def do_nothing():\n"
            "    pass\n"
        )

        res_verbose = perform_code_analysis(code_extra, smells_threshold='verbose')
        smells = res_verbose['code_smells']

        # Verify global numeric baseline (Magic Number)
        self.assertTrue(any(s['type'] == 'Magic Number' and '5432' in s['value'] for s in smells))

        # Verify raw zero array index
        self.assertTrue(any(s['type'] == 'Raw Zero Array Index' for s in smells))

        # Verify camelCase naming
        self.assertTrue(any(s['type'] == 'PEP 8 Naming Violation' and 'userScore' in s['value'] for s in smells))

        # Verify empty / dead-code function
        self.assertTrue(any(s['type'] == 'Empty Function / Dead Code' and 'do_nothing' in s['value'] for s in smells))
