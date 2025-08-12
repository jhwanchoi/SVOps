from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import time
import json


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
    'simple_workflow_example',
    default_args=default_args,
    description='Simple workflow example for SVOps platform',
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=['example', 'svops', 'simple'],
)


def print_start_message(**context):
    """Print workflow start message"""
    task_id = context.get('task_id', 'unknown')
    run_id = context['dag_run'].run_id
    conf = context['dag_run'].conf or {}
    
    print(f"🚀 Starting task: {task_id}")
    print(f"📋 Run ID: {run_id}")
    print(f"⚙️ Configuration: {json.dumps(conf, indent=2)}")
    
    # Extract parameters from configuration
    dataset_id = conf.get('dataset_id')
    task_id_param = conf.get('task_id')
    parameters = conf.get('parameters', {})
    
    if dataset_id:
        print(f"📁 Dataset ID: {dataset_id}")
    if task_id_param:
        print(f"🎯 Task ID: {task_id_param}")
    if parameters:
        print(f"🔧 Additional Parameters: {json.dumps(parameters, indent=2)}")
    
    print("✅ Workflow initialization completed")
    return "Workflow started successfully"


def simulate_processing(**context):
    """Simulate some processing work"""
    conf = context['dag_run'].conf or {}
    processing_time = conf.get('parameters', {}).get('processing_time', 30)
    
    print(f"🔄 Starting processing simulation...")
    print(f"⏱️ Processing time: {processing_time} seconds")
    
    # Simulate work with progress updates
    for i in range(int(processing_time)):
        if i % 10 == 0:
            progress = (i / processing_time) * 100
            print(f"📊 Progress: {progress:.1f}%")
        time.sleep(1)
    
    print("✅ Processing completed successfully")
    return f"Processing completed in {processing_time} seconds"


def print_results(**context):
    """Print workflow results"""
    run_id = context['dag_run'].run_id
    conf = context['dag_run'].conf or {}
    
    print(f"📊 Workflow Results Summary")
    print(f"🔖 Run ID: {run_id}")
    print(f"⏰ Completion Time: {datetime.now().isoformat()}")
    
    # Simulate some results
    results = {
        "status": "success",
        "processed_items": conf.get('parameters', {}).get('item_count', 100),
        "execution_time": conf.get('parameters', {}).get('processing_time', 30),
        "dataset_id": conf.get('dataset_id'),
        "task_id": conf.get('task_id')
    }
    
    print(f"📋 Results: {json.dumps(results, indent=2)}")
    print("🎉 Workflow completed successfully!")
    
    return results


def simulate_data_validation(**context):
    """Simulate data validation step"""
    conf = context['dag_run'].conf or {}
    dataset_id = conf.get('dataset_id')
    
    print(f"🔍 Starting data validation...")
    if dataset_id:
        print(f"📁 Validating dataset: {dataset_id}")
    
    # Simulate validation checks
    validation_steps = [
        "Checking data format",
        "Validating data integrity", 
        "Verifying data completeness",
        "Running quality checks"
    ]
    
    for step in validation_steps:
        print(f"✓ {step}")
        time.sleep(2)
    
    print("✅ Data validation completed successfully")
    return "Data validation passed"


# Define tasks
start_task = PythonOperator(
    task_id='start_workflow',
    python_callable=print_start_message,
    dag=dag,
)

validate_data_task = PythonOperator(
    task_id='validate_data',
    python_callable=simulate_data_validation,
    dag=dag,
)

process_data_task = PythonOperator(
    task_id='process_data',
    python_callable=simulate_processing,
    dag=dag,
)

# Simple bash task for environment check
check_environment_task = BashOperator(
    task_id='check_environment',
    bash_command="""
    echo "🔧 Environment Check"
    echo "📅 Date: $(date)"
    echo "💻 Hostname: $(hostname)"
    echo "👤 User: $(whoami)"
    echo "📂 Working Directory: $(pwd)"
    echo "🐍 Python Version: $(python3 --version)"
    echo "✅ Environment check completed"
    """,
    dag=dag,
)

finalize_task = PythonOperator(
    task_id='finalize_workflow',
    python_callable=print_results,
    dag=dag,
)

# Define task dependencies
start_task >> [validate_data_task, check_environment_task]
[validate_data_task, check_environment_task] >> process_data_task
process_data_task >> finalize_task