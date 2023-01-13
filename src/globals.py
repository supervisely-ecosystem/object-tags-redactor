import os
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
tag_metas = [
    tm
    for tm in project_meta.tag_metas
    if tm.applicable_to != sly.TagApplicableTo.IMAGES_ONLY
]
selected_classes = []

images = []
total_images = 0
current_image_idx = 0

dataset_id = sly.env.dataset_id(raise_not_found=False)
dataset_info = None
if dataset_id is None:
    datasets = api.dataset.get_list(project_id)
    images = [image for dataset in datasets for image in api.image.get_list(dataset.id)]
    total_images = len(images)
else:
    dataset_info = api.dataset.get_info_by_id(dataset_id)
    images = api.image.get_list(dataset_id)
    total_images = len(images)

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
