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
    'retries': 2,
    'retry_delay': timedelta(minutes=3),
}

# Create DAG
dag = DAG(
    'data_processing_pipeline',
    default_args=default_args,
    description='Data processing pipeline for SVOps platform',
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=['data', 'processing', 'svops'],
)


def extract_data(**context):
    """Simulate data extraction"""
    conf = context['dag_run'].conf or {}
    dataset_id = conf.get('dataset_id', 'default_dataset')
    
    print(f"📥 Starting data extraction...")
    print(f"📁 Dataset ID: {dataset_id}")
    
    # Simulate extraction time
    extraction_time = random.randint(10, 20)
    for i in range(extraction_time):
        if i % 5 == 0:
            print(f"📊 Extracting... {(i/extraction_time)*100:.0f}% complete")
        time.sleep(1)
    
    # Simulate extracted data info
    data_info = {
        "dataset_id": dataset_id,
        "records_extracted": random.randint(1000, 10000),
        "file_size_mb": random.randint(50, 500),
        "extraction_time": extraction_time
    }
    
    print(f"✅ Data extraction completed: {json.dumps(data_info, indent=2)}")
    return data_info


def transform_data(**context):
    """Simulate data transformation"""
    print(f"🔄 Starting data transformation...")
    
    # Get data from previous task
    ti = context['ti']
    data_info = ti.xcom_pull(task_ids='extract_data')
    
    if data_info:
        records = data_info.get('records_extracted', 1000)
        print(f"📊 Transforming {records} records...")
    
    # Simulate transformation steps
    transformation_steps = [
        "Cleaning data",
        "Normalizing formats",
        "Applying business rules",
        "Validating transformations",
        "Creating output files"
    ]
    
    for step in transformation_steps:
        print(f"🔧 {step}...")
        time.sleep(random.randint(3, 8))
    
    transformed_info = {
        "input_records": data_info.get('records_extracted', 0) if data_info else 0,
        "output_records": random.randint(800, 9500),
        "transformation_time": 25,
        "status": "success"
    }
    
    print(f"✅ Data transformation completed: {json.dumps(transformed_info, indent=2)}")
    return transformed_info


def load_data(**context):
    """Simulate data loading"""
    print(f"📤 Starting data loading...")
    
    # Get data from previous task
    ti = context['ti']
    transform_info = ti.xcom_pull(task_ids='transform_data')
    
    if transform_info:
        records = transform_info.get('output_records', 1000)
        print(f"📊 Loading {records} records...")
    
    # Simulate loading with progress
    loading_time = random.randint(15, 25)
    for i in range(loading_time):
        if i % 5 == 0:
            print(f"📤 Loading... {(i/loading_time)*100:.0f}% complete")
        time.sleep(1)
    
    load_info = {
        "records_loaded": transform_info.get('output_records', 0) if transform_info else 0,
        "loading_time": loading_time,
        "destination": "data_warehouse",
        "status": "success"
    }
    
    print(f"✅ Data loading completed: {json.dumps(load_info, indent=2)}")
    return load_info


def validate_pipeline(**context):
    """Validate the entire pipeline"""
    print(f"🔍 Starting pipeline validation...")
    
    # Get data from all previous tasks
    ti = context['ti']
    extract_info = ti.xcom_pull(task_ids='extract_data')
    transform_info = ti.xcom_pull(task_ids='transform_data')
    load_info = ti.xcom_pull(task_ids='load_data')
    
    # Perform validation checks
    validation_results = {
        "data_extracted": extract_info is not None,
        "data_transformed": transform_info is not None,
        "data_loaded": load_info is not None,
        "data_integrity": True,
        "performance_acceptable": True
    }
    
    # Check data flow
    if extract_info and transform_info and load_info:
        extracted = extract_info.get('records_extracted', 0)
        transformed = transform_info.get('output_records', 0)
        loaded = load_info.get('records_loaded', 0)
        
        print(f"📊 Data Flow Summary:")
        print(f"   Extracted: {extracted} records")
        print(f"   Transformed: {transformed} records")
        print(f"   Loaded: {loaded} records")
        
        # Simple data loss check
        data_loss_ratio = (extracted - loaded) / extracted if extracted > 0 else 0
        validation_results["data_loss_ratio"] = data_loss_ratio
        validation_results["data_integrity"] = data_loss_ratio < 0.1  # Less than 10% loss
    
    time.sleep(5)  # Simulate validation time
    
    print(f"✅ Pipeline validation completed: {json.dumps(validation_results, indent=2)}")
    return validation_results


def generate_report(**context):
    """Generate final pipeline report"""
    print(f"📊 Generating pipeline report...")
    
    # Get data from all tasks
    ti = context['ti']
    extract_info = ti.xcom_pull(task_ids='extract_data')
    transform_info = ti.xcom_pull(task_ids='transform_data')
    load_info = ti.xcom_pull(task_ids='load_data')
    validation_info = ti.xcom_pull(task_ids='validate_pipeline')
    
    conf = context['dag_run'].conf or {}
    run_id = context['dag_run'].run_id
    
    # Generate comprehensive report
    report = {
        "pipeline_run_id": run_id,
        "execution_date": datetime.now().isoformat(),
        "configuration": conf,
        "extraction": extract_info,
        "transformation": transform_info,
        "loading": load_info,
        "validation": validation_info,
        "overall_status": "SUCCESS" if validation_info and validation_info.get('data_integrity') else "WARNING"
    }
    
    print(f"📋 Final Pipeline Report:")
    print(json.dumps(report, indent=2))
    print(f"🎉 Pipeline execution completed!")
    
    return report


# Define tasks
extract_task = PythonOperator(
    task_id='extract_data',
    python_callable=extract_data,
    dag=dag,
)

setup_task = BashOperator(
    task_id='setup_environment',
    bash_command="""
    echo "🔧 Setting up processing environment..."
    echo " Creating temporary directories..."
    mkdir -p /tmp/svops_pipeline_{{ ds }}
    echo "🔍 Checking disk space..."
    df -h
    echo "💾 Checking memory..."
    free -h
    echo "✅ Environment setup completed"
    """,
    dag=dag,
)

transform_task = PythonOperator(
    task_id='transform_data',
    python_callable=transform_data,
    dag=dag,
)

load_task = PythonOperator(
    task_id='load_data',
    python_callable=load_data,
    dag=dag,
)

validate_task = PythonOperator(
    task_id='validate_pipeline',
    python_callable=validate_pipeline,
    dag=dag,
)

cleanup_task = BashOperator(
    task_id='cleanup_environment',
    bash_command="""
    echo "🧹 Cleaning up temporary files..."
    rm -rf /tmp/svops_pipeline_{{ ds }}
    echo "✅ Cleanup completed"
    """,
    dag=dag,
)

report_task = PythonOperator(
    task_id='generate_report',
    python_callable=generate_report,
    dag=dag,
)

# Define task dependencies
setup_task >> extract_task
extract_task >> transform_task
transform_task >> load_task
load_task >> validate_task
validate_task >> [cleanup_task, report_task]