
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# Import app logic
from app.prepare_export import prepare_export

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
}

dag = DAG(
    'training_pipeline',
    default_args=default_args,
    description='Export dataset and train model',
    schedule_interval=None, 
    catchup=False,
)

# ----------------- 1. Export Dataset -----------------
def run_export(**context):
    conf = context['dag_run'].conf or {}
    
    label_set = conf.get('label_set', 'default')
    fmt = conf.get('format', 'yolo')
    split = float(conf.get('split', 0.8))
    seed = int(conf.get('seed', 42))
    
    # Run export
    export_path = prepare_export(label_set, fmt=fmt, split_ratio=split, seed=seed)
    
    print(f"Dataset exported to: {export_path}")
    return str(export_path)

export_task = PythonOperator(
    task_id='export_dataset',
    python_callable=run_export,
    provide_context=True,
    dag=dag,
)

# ----------------- 2. Train Model -----------------
# We use BashOperator to run the training script in a separate process/environment if needed.
# The training script is expected to be at /opt/training/train.py

train_command = """
    python /opt/training/train.py \
    --data "{{ task_instance.xcom_pull(task_ids='export_dataset') }}/dataset.yaml" \
    --epochs {{ dag_run.conf.get('epochs', 10) }} \
    --imgsz 640
"""

train_task = BashOperator(
    task_id='train_model',
    bash_command=train_command,
    dag=dag,
)

# ----------------- 3. Register Model -----------------
# Placeholder for MLflow registration if not handled inside train.py
register_command = """
    echo "Model registration would happen here."
"""

register_task = BashOperator(
    task_id='register_model',
    bash_command=register_command,
    dag=dag,
)

export_task >> train_task >> register_task
