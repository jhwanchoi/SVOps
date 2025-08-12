from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import time
import json
import random


# Default arguments for the DAG
default_args = {
    'owner': 'svops',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Create DAG
dag = DAG(
    'ml_training_pipeline',
    default_args=default_args,
    description='Machine Learning training pipeline for SVOps platform',
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=['ml', 'training', 'svops'],
)


def prepare_training_data(**context):
    """Simulate training data preparation"""
    conf = context['dag_run'].conf or {}
    dataset_id = conf.get('dataset_id', 'ml_dataset')
    
    print(f"🔧 Preparing training data...")
    print(f"📁 Dataset ID: {dataset_id}")
    
    # Simulate data preparation steps
    preparation_steps = [
        "Loading dataset",
        "Cleaning data",
        "Feature engineering", 
        "Data splitting (train/val/test)",
        "Data normalization"
    ]
    
    for i, step in enumerate(preparation_steps):
        print(f"📊 Step {i+1}/{len(preparation_steps)}: {step}")
        time.sleep(random.randint(3, 7))
    
    # Simulate prepared data statistics
    data_stats = {
        "dataset_id": dataset_id,
        "total_samples": random.randint(10000, 100000),
        "train_samples": random.randint(7000, 70000),
        "val_samples": random.randint(1500, 15000),
        "test_samples": random.randint(1500, 15000),
        "features": random.randint(50, 200),
        "preparation_time": 25
    }
    
    print(f"✅ Data preparation completed: {json.dumps(data_stats, indent=2)}")
    return data_stats


def train_model(**context):
    """Simulate model training"""
    print(f"🤖 Starting model training...")
    
    # Get data from previous task
    ti = context['ti']
    data_stats = ti.xcom_pull(task_ids='prepare_training_data')
    
    if data_stats:
        train_samples = data_stats.get('train_samples', 10000)
        features = data_stats.get('features', 100)
        print(f"📊 Training with {train_samples} samples, {features} features")
    
    # Simulate training epochs
    epochs = random.randint(10, 20)
    print(f"🔄 Training for {epochs} epochs...")
    
    training_metrics = []
    for epoch in range(1, epochs + 1):
        # Simulate training progress
        train_loss = 1.0 - (epoch / epochs) * 0.7 + random.uniform(-0.05, 0.05)
        val_loss = 1.0 - (epoch / epochs) * 0.6 + random.uniform(-0.08, 0.08)
        accuracy = 0.3 + (epoch / epochs) * 0.6 + random.uniform(-0.03, 0.03)
        
        metrics = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "val_loss": round(val_loss, 4), 
            "accuracy": round(accuracy, 4)
        }
        training_metrics.append(metrics)
        
        if epoch % 5 == 0 or epoch == epochs:
            print(f"📈 Epoch {epoch}/{epochs}: Loss={train_loss:.4f}, Val_Loss={val_loss:.4f}, Acc={accuracy:.4f}")
        
        time.sleep(2)
    
    # Final model info
    model_info = {
        "model_type": "neural_network",
        "epochs_trained": epochs,
        "final_accuracy": training_metrics[-1]["accuracy"],
        "final_loss": training_metrics[-1]["train_loss"],
        "training_time_minutes": epochs * 2 / 60,
        "model_size_mb": random.randint(50, 500),
        "training_metrics": training_metrics
    }
    
    print(f"✅ Model training completed: {json.dumps(model_info, indent=2)}")
    return model_info


def evaluate_model(**context):
    """Simulate model evaluation"""
    print(f"📊 Starting model evaluation...")
    
    # Get data from previous tasks
    ti = context['ti']
    data_stats = ti.xcom_pull(task_ids='prepare_training_data')
    model_info = ti.xcom_pull(task_ids='train_model')
    
    if data_stats and model_info:
        test_samples = data_stats.get('test_samples', 2000)
        final_accuracy = model_info.get('final_accuracy', 0.8)
        print(f"🧪 Evaluating on {test_samples} test samples")
    
    # Simulate evaluation steps
    evaluation_steps = [
        "Loading test dataset",
        "Running model inference",
        "Calculating metrics",
        "Generating confusion matrix",
        "Creating evaluation report"
    ]
    
    for step in evaluation_steps:
        print(f"🔍 {step}...")
        time.sleep(random.randint(2, 5))
    
    # Simulate evaluation results
    evaluation_results = {
        "test_accuracy": round(final_accuracy + random.uniform(-0.05, 0.02), 4),
        "test_precision": round(final_accuracy + random.uniform(-0.03, 0.03), 4),
        "test_recall": round(final_accuracy + random.uniform(-0.04, 0.02), 4),
        "test_f1_score": round(final_accuracy + random.uniform(-0.02, 0.02), 4),
        "inference_time_ms": random.randint(5, 50),
        "model_complexity": "medium",
        "evaluation_passed": True
    }
    
    print(f"✅ Model evaluation completed: {json.dumps(evaluation_results, indent=2)}")
    return evaluation_results


def validate_model_performance(**context):
    """Validate if model meets performance criteria"""
    print(f"✅ Validating model performance...")
    
    # Get evaluation results
    ti = context['ti']
    evaluation_results = ti.xcom_pull(task_ids='evaluate_model')
    
    if not evaluation_results:
        raise ValueError("No evaluation results found")
    
    # Define performance thresholds
    min_accuracy = 0.75
    max_inference_time = 100  # ms
    
    accuracy = evaluation_results.get('test_accuracy', 0.0)
    inference_time = evaluation_results.get('inference_time_ms', 0)
    
    print(f"📊 Performance Check:")
    print(f"   Accuracy: {accuracy} (minimum: {min_accuracy})")
    print(f"   Inference Time: {inference_time}ms (maximum: {max_inference_time}ms)")
    
    # Validation checks
    validation_results = {
        "accuracy_check": accuracy >= min_accuracy,
        "performance_check": inference_time <= max_inference_time,
        "overall_validation": accuracy >= min_accuracy and inference_time <= max_inference_time
    }
    
    if validation_results["overall_validation"]:
        print("✅ Model validation PASSED - Ready for deployment")
    else:
        print("❌ Model validation FAILED - Requires improvement")
    
    time.sleep(3)
    return validation_results


def save_model_artifacts(**context):
    """Simulate saving model artifacts"""
    print(f"💾 Saving model artifacts...")
    
    # Get all results
    ti = context['ti']
    model_info = ti.xcom_pull(task_ids='train_model')
    evaluation_results = ti.xcom_pull(task_ids='evaluate_model')
    validation_results = ti.xcom_pull(task_ids='validate_model_performance')
    
    conf = context['dag_run'].conf or {}
    run_id = context['dag_run'].run_id
    
    # Simulate saving artifacts
    artifacts = [
        "model_weights.pkl",
        "model_config.json", 
        "training_history.json",
        "evaluation_report.json",
        "model_metadata.json"
    ]
    
    for artifact in artifacts:
        print(f"💾 Saving {artifact}...")
        time.sleep(1)
    
    # Create model registry entry
    model_registry = {
        "model_id": f"ml_model_{run_id}",
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "dataset_id": conf.get('dataset_id'),
        "model_info": model_info,
        "evaluation_results": evaluation_results,
        "validation_results": validation_results,
        "artifacts_saved": artifacts,
        "ready_for_deployment": validation_results.get('overall_validation', False) if validation_results else False
    }
    
    print(f"✅ Model artifacts saved: {json.dumps(model_registry, indent=2)}")
    return model_registry


# Define tasks
prepare_data_task = PythonOperator(
    task_id='prepare_training_data',
    python_callable=prepare_training_data,
    dag=dag,
)

setup_ml_env_task = BashOperator(
    task_id='setup_ml_environment',
    bash_command="""
    echo "🔧 Setting up ML training environment..."
    echo "🐍 Python version: $(python3 --version)"
    echo "📦 Checking GPU availability..."
    echo "💾 Checking available memory..."
    free -h
    echo "📂 Creating model output directory..."
    mkdir -p /tmp/ml_models_{{ ds }}
    echo "✅ ML environment setup completed"
    """,
    dag=dag,
)

train_model_task = PythonOperator(
    task_id='train_model',
    python_callable=train_model,
    dag=dag,
)

evaluate_model_task = PythonOperator(
    task_id='evaluate_model',
    python_callable=evaluate_model,
    dag=dag,
)

validate_performance_task = PythonOperator(
    task_id='validate_model_performance',
    python_callable=validate_model_performance,
    dag=dag,
)

save_artifacts_task = PythonOperator(
    task_id='save_model_artifacts',
    python_callable=save_model_artifacts,
    dag=dag,
)

cleanup_ml_env_task = BashOperator(
    task_id='cleanup_ml_environment',
    bash_command="""
    echo "🧹 Cleaning up ML training environment..."
    rm -rf /tmp/ml_models_{{ ds }}
    echo "✅ ML environment cleanup completed"
    """,
    dag=dag,
)

# Define task dependencies
setup_ml_env_task >> prepare_data_task
prepare_data_task >> train_model_task
train_model_task >> evaluate_model_task
evaluate_model_task >> validate_performance_task
validate_performance_task >> save_artifacts_task
save_artifacts_task >> cleanup_ml_env_task