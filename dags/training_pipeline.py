
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

# ----------------- 0. Checkout Data Version -----------------
# Checkout the specific dataset version from DVC/Git
checkout_command = """
    cd /opt && \
    git config --global --add safe.directory /opt && \
    if [ "{{ dag_run.conf.get('version', 'None') }}" != "None" ]; then \
        echo "Checking out version {{ dag_run.conf.get('version') }}"; \
        git checkout {{ dag_run.conf.get('version') }}; \
    fi && \
    dvc checkout || echo "DVC Checkout failed or no changes"
"""

checkout_task = BashOperator(
    task_id='checkout_dataset',
    bash_command=checkout_command,
    dag=dag,
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
# Model is pre-downloaded manually to /opt/model/yolov8n.pt (mounted from mlops/model/)
# The training script is expected to be at /opt/training/train.py

train_command = """
    python /opt/training/train.py \
    --data "{{ task_instance.xcom_pull(task_ids='export_dataset') }}/dataset.yaml" \
    --epochs {{ dag_run.conf.get('epochs', 10) }} \
    --imgsz 640 \
    --register-name "{{ dag_run.conf.get('model_name', 'YOLOv8_Model') }}"
"""

train_task = BashOperator(
    task_id='train_model',
    bash_command=train_command,
    dag=dag,
)

checkout_task >> export_task >> train_task
