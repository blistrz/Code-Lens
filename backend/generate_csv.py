import pandas as pd
import numpy as np

def create_ultimate_dataset():
    print("Generating 1 Lakh (100,000) Enterprise-Grade samples with 7 Features...")
    
    # 1. CLEAN DATA (45,000 rows)
    clean_loc = np.random.randint(5, 30, 45000)
    clean_complexity = np.random.randint(1, 5, 45000)
    clean_args = np.random.randint(0, 4, 45000)
    clean_depth = np.random.randint(0, 3, 45000)        # Max 2 levels deep
    clean_returns = np.random.randint(0, 3, 45000)      # 0 to 2 returns
    clean_vars = np.random.randint(1, 5, 45000)         # Few variables
    clean_calls = np.random.randint(0, 4, 45000)        # Low coupling
    clean_labels = np.zeros(45000, dtype=int)
    
    clean_df = pd.DataFrame({
        'loc': clean_loc, 'complexity': clean_complexity, 'args': clean_args,
        'nesting_depth': clean_depth, 'returns': clean_returns,
        'variables': clean_vars, 'methods_called': clean_calls, 'is_smelly': clean_labels
    })

    # 2. SMELLY DATA (45,000 rows)
    smelly_loc = np.random.randint(60, 300, 45000)
    smelly_complexity = np.random.randint(10, 40, 45000)
    smelly_args = np.random.randint(5, 12, 45000)
    smelly_depth = np.random.randint(4, 10, 45000)      # Deeply nested (Spaghetti)
    smelly_returns = np.random.randint(4, 15, 45000)    # Too many exits
    smelly_vars = np.random.randint(10, 30, 45000)      # Too many variables
    smelly_calls = np.random.randint(8, 25, 45000)      # High coupling
    smelly_labels = np.ones(45000, dtype=int)
    
    smelly_df = pd.DataFrame({
        'loc': smelly_loc, 'complexity': smelly_complexity, 'args': smelly_args,
        'nesting_depth': smelly_depth, 'returns': smelly_returns,
        'variables': smelly_vars, 'methods_called': smelly_calls, 'is_smelly': smelly_labels
    })

    # 3. EDGE CASES (10,000 rows)
    edge_loc = np.random.randint(5, 300, 10000)
    edge_complexity = np.random.randint(1, 40, 10000)
    edge_args = np.random.randint(0, 12, 10000)
    edge_depth = np.random.randint(0, 10, 10000)
    edge_returns = np.random.randint(0, 15, 10000)
    edge_vars = np.random.randint(0, 30, 10000)
    edge_calls = np.random.randint(0, 25, 10000)
    
    # Complex Smelly Rules for Edge Cases
    edge_labels = (
        (edge_loc > 75) | 
        (edge_complexity > 12) | 
        (edge_depth > 4) | 
        (edge_args > 6) | 
        (edge_returns > 5)
    ).astype(int)
    
    edge_df = pd.DataFrame({
        'loc': edge_loc, 'complexity': edge_complexity, 'args': edge_args,
        'nesting_depth': edge_depth, 'returns': edge_returns,
        'variables': edge_vars, 'methods_called': edge_calls, 'is_smelly': edge_labels
    })

    # Combine, Shuffle, and Save
    final_df = pd.concat([clean_df, smelly_df, edge_df]).sample(frac=1).reset_index(drop=True)
    
    # Check that columns match the MetricVisitor exact order
    final_df = final_df[['loc', 'complexity', 'args', 'nesting_depth', 'returns', 'variables', 'methods_called', 'is_smelly']]
    
    final_df.to_csv('dataset.csv', index=False)
    print(f"✅ Created ultimate 'dataset.csv' with {len(final_df):,} rows!")

if __name__ == "__main__":
    create_ultimate_dataset()