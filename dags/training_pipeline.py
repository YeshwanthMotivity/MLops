
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
    export PATH=$PATH:/home/airflow/.local/bin && \
    cd /opt/mlops && \
    dvc remote modify --local localremote url ${DVC_REMOTE_URL} && \
    git config --global --add safe.directory /opt/mlops && \
    if [ "{{ dag_run.conf.get('version', 'None') }}" != "None" ]; then \
        echo "Checking out version {{ dag_run.conf.get('version') }}"; \
        git checkout {{ dag_run.conf.get('version') }}; \
    fi && \
    dvc checkout
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
# The training script is expected to be at /opt/mlops/training/train.py

train_command = """
    set -e -o pipefail
    python /opt/mlops/training/train.py \
    --data "{{ task_instance.xcom_pull(task_ids='export_dataset') }}/dataset.yaml" \
    --epochs {{ dag_run.conf.get('epochs', 5) }} \
    --imgsz 640 2>&1 | tee /tmp/train.log
    
    RUN_ID=$(grep "MLFLOW_RUN_ID:" /tmp/train.log | tail -n 1 | awk '{print $NF}' | tr -d '\\r\\n')
    if [ -z "$RUN_ID" ]; then
        echo "❌ Error: MLFLOW_RUN_ID not found in logs"
        exit 1
    fi
    echo $RUN_ID
"""

train_task = BashOperator(
    task_id='train_model',
    bash_command=train_command,
    do_xcom_push=True,
    dag=dag,
)

# ----------------- 3. Register Model -----------------
register_command = """
    python /opt/mlops/training/register_model.py \
    --run-id "{{ task_instance.xcom_pull(task_ids='train_model') }}" \
    --model-name "{{ dag_run.conf.get('model_name', 'YOLOv8_Model') }}"
"""

register_task = BashOperator(
    task_id='register_model',
    bash_command=register_command,
    dag=dag,
)

checkout_task >> export_task >> train_task >> register_task
