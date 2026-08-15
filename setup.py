"""
setup.py — One-click setup script for the DTMS project.
1. Creates database and seeds the fleet
2. Builds the synthetic dataset
3. Trains all ML models
"""

import os
import sys

def run_step(cmd, name):
    print(f"\n{'='*60}")
    print(f"RUNNING: {name}")
    print(f"{'='*60}")
    ret = os.system(cmd)
    if ret != 0:
        print(f"\nFAILED: {name}")
        sys.exit(1)
    print(f"SUCCESS: {name}")

if __name__ == "__main__":
    # Force UTF-8 stdout if needed, though stripping emojis is safer
    import io
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding='utf-8')
        
    run_step(f"{sys.executable} src/database/init_db.py", "1. Database Initialization")
    run_step(f"{sys.executable} src/pipeline/dataset_builder.py", "2. Building Synthetic Dataset (This may take a minute)")
    run_step(f"{sys.executable} src/ml/train_anomaly.py", "3. Training Tier 1 ML: Isolation Forest")
    run_step(f"{sys.executable} src/ml/train_classifier.py", "4. Training Tier 2 ML: XGBoost Classifier")
    run_step(f"{sys.executable} src/ml/train_rul.py", "5. Training Tier 3 ML: RUL Regressors")
    
    print(f"\n{'='*60}")
    print("SETUP COMPLETE!")
    print(f"{'='*60}")
    print("\nYou can now start the system:")
    print("  Terminal 1 (Backend):  uvicorn src.api.main:app --port 8000")
    print("  Terminal 2 (Frontend): streamlit run src/dashboard/Home.py")
    print("\nOr just run `python run.py` to start both!")
