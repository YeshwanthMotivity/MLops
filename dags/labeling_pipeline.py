
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.sensors.python import PythonSensor
from airflow.utils.trigger_rule import TriggerRule

# Import your app logic
# Ensure /opt/dataset-platform is in PYTHONPATH (e.g., via docker-compose)
from app.ingest import ingest
from app.create_batch import create_batch
from app.integrations.cvat.create_task import create_labeling_task
from app.pull_annotations import pull_annotations
from app.integrations.cvat.client import CvatClient
from app.config import BATCHES
import yaml

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'labeling_pipeline',
    default_args=default_args,
    description='End-to-end active learning loop: Ingest -> Batch -> CVAT -> Pull',
    schedule_interval=None,  # Trigger manually or via API
    catchup=False,
)

# ----------------- 1. Ingest -----------------
def run_ingest(**context):
    conf = context['dag_run'].conf or {}
    source_id = conf.get('source_id', 'manual_upload')
    count = ingest(source_id)
    print(f"Ingested {count} new images.")
    return count

ingest_task = PythonOperator(
    task_id='ingest_images',
    python_callable=run_ingest,
    provide_context=True,
    dag=dag,
)

# ----------------- 2. Create Batch -----------------
def run_create_batch(**context):
    conf = context['dag_run'].conf or {}
    label_set = conf.get('label_set', 'default')
    batch_size = conf.get('batch_size', 10)
    
    batch_id = create_batch(label_set, limit=batch_size)
    
    if not batch_id:
        print("No images to label. Stopping.")
        return None  # Branching could skip downstream, but for now we just pass None
    
    return batch_id

create_batch_task = PythonOperator(
    task_id='create_batch',
    python_callable=run_create_batch,
    provide_context=True,
    dag=dag,
)

# ----------------- 3. Push to CVAT -----------------
def run_cvat_task(**context):
    # Get batch_id from previous task
    batch_id = context['task_instance'].xcom_pull(task_ids='create_batch')
    if not batch_id:
        print("No batch created. Skipping CVAT task creation.")
        return None

    conf = context['dag_run'].conf or {}
    dataset_name = conf.get('cvat_project', 'MyProject')
    labels = conf.get('labels', ['car', 'truck', 'bus']) # Default list

    task_id = create_labeling_task(dataset_name, batch_id, labels)
    return task_id

cvat_task = PythonOperator(
    task_id='create_cvat_task',
    python_callable=run_cvat_task,
    provide_context=True,
    dag=dag,
)

# ----------------- 4. Wait for Completion -----------------
def check_cvat_completion(**context):
    batch_id = context['task_instance'].xcom_pull(task_ids='create_batch')
    if not batch_id:
        return True # Skip if no batch
    
    # We need the CVAT task ID. It's returned by create_cvat_task, 
    # but also saved in info.yaml. Let's rely on reading info.yaml or XCom.
    cvat_task_id = context['task_instance'].xcom_pull(task_ids='create_cvat_task')
    
    if not cvat_task_id:
        # Fallback: try to read from batch info (in case of re-run where create_task matched existing)
        # But for now, let's assume if xcom is None, we didn't start a task.
        return True

    client = CvatClient()
    jobs = client.get_task_jobs(cvat_task_id)
    
    if not jobs:
        return False
        
    total = len(jobs)
    done = sum(1 for j in jobs if j.get("state") == "completed")
    
    print(f"Batch {batch_id} (Task {cvat_task_id}): {done}/{total} jobs completed.")
    return done == total

wait_for_annotation = PythonSensor(
    task_id='wait_for_annotation',
    python_callable=check_cvat_completion,
    poke_interval=60, # Check every minute
    timeout=60 * 60 * 24 * 7, # Wait up to a week
    mode='reschedule', # Release worker slot while waiting
    dag=dag,
)

# ----------------- 5. Pull Annotations -----------------
def run_pull(**context):
    batch_id = context['task_instance'].xcom_pull(task_ids='create_batch')
    if not batch_id:
        return 0
        
    # We can trust that if we reached here, the task is done (thanks to sensor)
    count = pull_annotations(batch_id, force=False)
    return count

pull_task = PythonOperator(
    task_id='pull_annotations',
    python_callable=run_pull,
    provide_context=True,
    trigger_rule=TriggerRule.ALL_SUCCESS,
    dag=dag,
)

# ----------------- 6. DVC Commit -----------------
# Commit the new labels to DVC and Git
commit_command = """
    cd /opt/dataset-platform && \
    dvc add ../storage && \
    dvc push && \
    git config --global --add safe.directory /opt && \
    git config --global user.email "airflow@example.com" && \
    git config --global user.name "Airflow Automation" && \
    git add ../storage.dvc && \
    git commit -m "Auto-commit: Labelling batch {{ task_instance.xcom_pull(task_ids='create_batch') }}" || echo "No changes to commit"
"""

commit_task = BashOperator(
    task_id='dvc_commit',
    bash_command=commit_command,
    trigger_rule=TriggerRule.ALL_SUCCESS,
    dag=dag,
)

# Flow
ingest_task >> create_batch_task >> cvat_task >> wait_for_annotation >> pull_task >> commit_task
