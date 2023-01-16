import json
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv
import supervisely as sly


zoom_factor = 1.2
exclude_geometries = [sly.Polyline.geometry_name()]

# for convenient debug, has no effect in production
if sly.utils.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))

api = sly.Api()
team_id = sly.env.team_id()
user_info = api.user.get_my_info()
data_dir = sly.app.get_data_dir()
workspace_id = sly.env.workspace_id()
project_id = sly.env.project_id()
project_meta_json = api.project.get_meta(project_id)
project_meta = sly.ProjectMeta.from_json(project_meta_json)
project_info = api.project.get_info_by_id(project_id)
app_path = os.path.join(data_dir, "object-tags-editor-files")
pr_path = os.path.join(app_path, f"project-{project_info.id}")
if not os.path.exists(pr_path):
    os.makedirs(pr_path)
tag_metas = [
    tm
    for tm in project_meta.tag_metas
    if tm.applicable_to != sly.TagApplicableTo.IMAGES_ONLY
]
selected_classes = []


def load_images_stat():
    remote_filepath = Path(pr_path).joinpath(f"images_stat.json").as_posix()
    if not api.file.exists(team_id, "/" + remote_filepath):
        return set()
    api.file.download(team_id, "/" + remote_filepath, remote_filepath)
    with open(remote_filepath, "r") as file:
        data = json.load(file)
    os.remove(remote_filepath)
    print(data)
    return set(data)


completed_images = load_images_stat()
images = 0
total_images = 0
current_image_idx = 0

dataset_id = sly.env.dataset_id(raise_not_found=False)
dataset_info = None


def load_images():
    global images
    global current_image_idx
    global total_images
    global dataset_info
    global completed_images
    if dataset_id is None:
        datasets = api.dataset.get_list(project_id)
        all_images = [
            image for dataset in datasets for image in api.image.get_list(dataset.id)
        ]
    else:
        dataset_info = api.dataset.get_info_by_id(dataset_id)
        all_images = api.image.get_list(dataset_id)
    images = [image for image in all_images if image.id in completed_images]
    completed_images = set([image.id for image in images])
    current_image_idx = max(0, len(images))
    images.extend([image for image in all_images if image.id not in completed_images])
    current_image_idx = min(current_image_idx, len(images) - 1)
    total_images = len(images)


load_images()

current_annotation = None
objects = []
total_objects = 0
current_object_idx = 0


def set_image():
    if len(images) == 0:
        return
    global current_annotation
    global current_object_idx
    global objects
    global total_objects
    current_annotation = get_annotation()
    objects = filter_labels(current_annotation.labels)
    current_object_idx = 0
    total_objects = len(objects)


def get_annotation():
    image_id = images[current_image_idx].id
    ann_json = api.annotation.download_json(image_id)
    ann = sly.Annotation.from_json(ann_json, project_meta)
    return ann


def is_permitted_geometry(geometry_type):
    if geometry_type in exclude_geometries:
        return False
    return True


def is_selected_class(class_name: str):
    if len(selected_classes) == 0:
        return True
    if class_name in selected_classes:
        return True
    return False


def filter_labels(labels: List[sly.Label]):
    return [
        label
        for label in labels
        if is_selected_class(label.obj_class.name)
        and is_permitted_geometry(label.geometry.geometry_name())
    ]


def save_images_stat():
    remote_filepath = Path(pr_path).joinpath(f"images_stat.json").as_posix()
    data = list(completed_images)
    with open(remote_filepath, "w+") as file:
        json.dump(data, file)
    if api.file.exists(team_id, remote_filepath):
        api.file.remove(team_id, remote_filepath)
    api.file.upload(team_id, remote_filepath, remote_filepath)
    os.remove(remote_filepath)
