import yaml
from app.config import BATCHES
from app.integrations.cvat.client import CvatClient
from app.integrations.cvat.paths import get_cvat_image_paths


def create_labeling_task(dataset_name: str, batch_id: str, labels: list[str]):
    """
    Production labeling entrypoint.
    Airflow will call this.
    """

    client = CvatClient()

    #  ensure dataset(project)
    project_id = client.ensure_project(dataset_name, labels)

    #  create batch task
    task_id = client.create_task(project_id, batch_id)

    #  attach images
    paths = get_cvat_image_paths(batch_id)
    client.attach_images(task_id, paths)

    #  save task_id into batch info.yaml
    info_path = BATCHES / batch_id / "info.yaml"
    if info_path.exists():
        with open(info_path) as f:
            info = yaml.safe_load(f)
        info["cvat_task_id"] = task_id
        with open(info_path, "w") as f:
            yaml.dump(info, f)
        print(f"Saved cvat_task_id={task_id} to {info_path.name}")

    print(f"Dataset: {dataset_name} | Batch: {batch_id} | Task: {task_id}")
    return task_id


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create a CVAT labeling task for a batch")
    parser.add_argument("--dataset", required=True, help="CVAT project name")
    parser.add_argument("--batch-id", required=True, help="Batch ID from batches/")
    parser.add_argument("--labels", required=True, nargs="+", help="Label names (e.g. car truck bus)")
    args = parser.parse_args()

    create_labeling_task(args.dataset, args.batch_id, args.labels)
