import os
from dotenv import load_dotenv
import supervisely as sly


zoom_factor = 1.2

# for convenient debug, has no effect in production
if sly.utils.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))

api = sly.Api()
project_id = sly.env.project_id()
project_meta_json = api.project.get_meta(project_id)
project_meta = sly.ProjectMeta.from_json(project_meta_json)
project_info = api.project.get_info_by_id(project_id)
tag_metas = [tm for tm in project_meta.tag_metas if tm.applicable_to != sly.TagApplicableTo.IMAGES_ONLY]

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
total_objectss = 0
current_object_idx = 0

def set_image():
    if len(images) == 0:
        return
    global current_annotation
    global current_object_idx
    global objects
    global total_objectss
    current_annotation = get_annotation()
    objects = current_annotation.labels
    current_object_idx = 0
    total_objectss = len(current_annotation.labels)


def get_annotation():
    image_id = images[current_image_idx].id
    ann_json = api.annotation.download_json(image_id)
    ann = sly.Annotation.from_json(ann_json, project_meta)
    ann = filter_labels(ann)
    return ann


def filter_labels(ann):
    labels = [
        label
        for label in ann.labels
        if not label.obj_class.geometry_type is sly.Polyline
    ]
    for label in ann.labels:
        ann = ann.delete_label(label)
    ann = ann.add_labels(labels)
    return ann
