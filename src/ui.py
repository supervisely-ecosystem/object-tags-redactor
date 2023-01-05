import supervisely as sly
from supervisely.app.widgets import (
    Container,
    LabeledImage,
    Text,
    Card,
    Button,
    Flexbox,
    ProjectThumbnail,
    DatasetThumbnail,
    InputTag,
    NotificationBox
)
import src.globals as g

# thumbnail
thumbnail = None
if g.dataset_id is None:
    thumbnail = ProjectThumbnail(g.project_info)
else:
    thumbnail = DatasetThumbnail(g.project_info, g.dataset_info)
thumbnail_card = Card(title="Input", content=thumbnail)

# images buttons
image_progress = Text(f"Image:  {g.current_image_idx + 1} / {g.total_images}")
next_image_button = Button(text=">>")
prev_image_button = Button(text="<<")
images_buttons = Flexbox(widgets=[prev_image_button, image_progress, next_image_button])

# objects buttons
object_progress = Text(f"Obect: {g.current_object_idx + 1} / {g.total_objectss}")
next_object_btn = Button(text=">>")
prev_object_btn = Button(text="<<")
object_buttons = Flexbox(widgets=[prev_object_btn, object_progress, next_object_btn])

# object selector card
buttons = Container(widgets=[images_buttons, object_buttons])
object_selector_card = Card(
    content=Container(widgets=[buttons]),
    title="Select Object"
)

# tags input card
tag_inputs = [InputTag(tag_meta) for tag_meta in g.project_meta.tag_metas]
disclaimer = NotificationBox(
    title="Warning",
    description="Objects will be modified in-place! Make sure you backed up your data.",
    box_type="warning",
)
save_button = Button(text="Save tags")
success_message = Text("Tags saved!", status="success")
success_message.hide()
save_container = Container(widgets=[disclaimer, Flexbox(widgets=[save_button, success_message])])
tags_container = Container(widgets=tag_inputs)
tags_card = Card(content=Container(widgets=[tags_container, save_container], gap=40), title="Object tags")

# labeled image card
labeled_image = LabeledImage()
labeled_image_card = Card(content=labeled_image, title="Object preview")

# main window
main_window = Container(widgets=[labeled_image_card, tags_card], direction="horizontal", fractions=[1, 1])
main_window_card = Card(title="Edit Tags", content=main_window)

def loading(*components):
    def dec(func):
        def inner(*args, **kwargs):
            for component in components:
                component.loading = True
            result = func(*args, **kwargs)
            for component in components:
                component.loading = False
            return result

        return inner

    return dec

def render_image():
    label = g.current_annotation.labels[g.current_object_idx]
    label_id = label.to_json()["id"]
    image = g.images[g.current_image_idx]
    image_url = image.preview_url
    image_id = image.id
    
    object_progress.set(
        f"Object: {g.current_object_idx+1} / {g.total_objectss}", status="text"
    )
    labeled_image.set(
        title=f"{image.name}",
        image_url=image_url,
        ann=g.current_annotation,
        image_id=image_id,
        zoom_to=label_id,
        zoom_factor=g.zoom_factor,
    )

def render_tags():
    label = g.current_annotation.labels[g.current_object_idx]
    label_class = label.obj_class

    for i, tm in enumerate(g.project_meta.tag_metas):
        if tm.applicable_to == sly.TagApplicableTo.OBJECTS_ONLY:
            if label_class.name in tm.applicable_classes:
                tag_inputs[i].show()
            else:
                tag_inputs[i].hide()
        else:
            tag_inputs[i].show()
        tag = label.tags.get(tm.name)
        tag_inputs[i].set(tag=tag)

    success_message.hide()

def render_selected_object():
    render_image()
    render_tags()

def render_selected_image():
    image_progress.set(
        f"Image: {g.current_image_idx + 1} / {g.total_images}", status="text"
    )
    render_selected_object()

@loading(object_buttons, labeled_image_card, tags_card)
def select_object(idx):
    g.current_object_idx = idx
    render_selected_object()

@loading(buttons, labeled_image_card, tags_card)
def select_image(idx):
    g.current_image_idx = idx
    g.set_image()
    render_selected_image()

@save_button.click
def save_object_tags():
    updated_tags = sly.TagCollection()
    for i, tm in enumerate(g.project_meta.tag_metas):
        tag_value = tag_inputs[i].get_value()
        if tag_value is not None:
            if type(tag_value) is bool:
                tag_value = None
            tag = sly.Tag(tm, tag_value)
            updated_tags.add(tag)

    current_label = g.current_annotation.labels[g.current_object_idx]
    labels_after_current = g.current_annotation.labels[g.current_object_idx + 1 :]
    g.current_annotation = g.current_annotation.delete_label(current_label)
    for label in labels_after_current:
        g.current_annotation = g.current_annotation.delete_label(label)
    g.current_annotation = g.current_annotation.add_label(
        current_label.clone(tags=updated_tags)
    )
    g.current_annotation = g.current_annotation.add_labels(labels_after_current)
    image_id = g.images[g.current_image_idx].id
    g.api.annotation.upload_ann(image_id, g.current_annotation)

    select_object(g.current_object_idx)
    success_message.show()

@next_object_btn.click
def next_object():
    if g.current_object_idx == g.total_objectss - 1:
        return
    select_object(g.current_object_idx + 1)

@prev_object_btn.click
def prev_object():
    if g.current_object_idx == 0:
        return
    select_object(g.current_object_idx - 1)

@next_image_button.click
def next_image():
    if g.current_image_idx == g.total_images - 1:
        return
    select_image(g.current_image_idx + 1)

@prev_image_button.click
def prev_image():
    if g.current_image_idx == 0:
        return
    select_image(g.current_image_idx - 1)
