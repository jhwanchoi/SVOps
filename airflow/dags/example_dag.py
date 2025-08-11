from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.http import SimpleHttpOperator


default_args = {
    'owner': 'svops',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'example_svops_dag',
    default_args=default_args,
    description='Example DAG for SVOps',
    schedule_interval='@daily',
    catchup=False,
)


def print_hello():
    print("Hello from SVOps Airflow!")
    return "Hello World"


def print_date():
    print(f"Current date: {datetime.now()}")
    return datetime.now().isoformat()


hello_task = PythonOperator(
    task_id='hello_task',
    python_callable=print_hello,
    dag=dag,
)

date_task = PythonOperator(
    task_id='date_task',
    python_callable=print_date,
    dag=dag,
)

api_health_check = SimpleHttpOperator(
    task_id='api_health_check',
    http_conn_id='backend_api',
    endpoint='/health',
    method='GET',
    dag=dag,
)

hello_task >> date_task >> api_health_check