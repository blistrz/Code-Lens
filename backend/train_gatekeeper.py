import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib

def train_ultimate_model():
    print("Reading Kaggle Software Defect Dataset...")
    try:
        df = pd.read_csv('kaggle_dataset.csv') 
    except FileNotFoundError:
        print("❌ Error: kaggle_dataset.csv not found in this folder.")
        return

    feature_columns = [
        'lines_of_code', 
        'cyclomatic_complexity', 
        'num_functions', 
        'num_classes', 
        'avg_function_length'
    ]
    
    df = df.dropna(subset=feature_columns + ['defect'])
    
    # --- THE FYP FIX: DATA BALANCING (UNDERSAMPLING) ---
    print("⚖️ Balancing the dataset so the AI doesn't cheat...")
    
    # 1. Separate the good from the bad
    df_clean = df[df['defect'] == 0]
    df_smelly = df[df['defect'] == 1]
    
    # 2. Find whichever group has fewer examples
    min_samples = min(len(df_clean), len(df_smelly))
    
    # 3. Randomly grab exactly that many from both groups so it's a perfect 50/50 split
    df_clean_balanced = df_clean.sample(n=min_samples, random_state=42)
    df_smelly_balanced = df_smelly.sample(n=min_samples, random_state=42)
    
    # 4. Mash them back together and shuffle!
    df_balanced = pd.concat([df_clean_balanced, df_smelly_balanced]).sample(frac=1, random_state=42)
    # ---------------------------------------------------

    X = df_balanced[feature_columns] 
    y = df_balanced['defect']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("🧠 Training the 5-Feature Enterprise Gatekeeper...")
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    
    print(f"\n✅ Training Complete. Model Accuracy: {accuracy * 100:.2f}%")
    print("\n📊 --- FYP Defense Report (Take a screenshot of THIS one!) ---")
    print(classification_report(y_test, predictions, target_names=["Clean Code", "Defective/Smelly"]))

    joblib.dump(model, 'code_smell_model.pkl')
    print("💾 Gatekeeper saved as 'code_smell_model.pkl'")

if __name__ == "__main__":
    train_ultimate_model()