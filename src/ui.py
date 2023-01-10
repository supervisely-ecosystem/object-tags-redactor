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
    NotificationBox,
    ClassesTable
)
import src.globals as g

# thumbnail
thumbnail = None
if g.dataset_id is None:
    thumbnail = ProjectThumbnail(g.project_info)
else:
    thumbnail = DatasetThumbnail(g.project_info, g.dataset_info)
thumbnail_card = Card(title="Input", content=thumbnail)

# classes selector
classes_selector = ClassesTable(project_id = g.project_id)
select_classes_button = Button("Select")
classes_selector_card = Card(title="Select Classes", content=Container(
    widgets=[classes_selector, select_classes_button]
))

@select_classes_button.click
def select_classes():
    g.selected_classes = classes_selector.get_selected_classes()
    select_image(g.current_image_idx)

# images buttons
image_progress = Text(f"Image:  0 / 0")
next_image_button = Button(text=">>")
prev_image_button = Button(text="<<")
images_buttons = Flexbox(widgets=[prev_image_button, image_progress, next_image_button])

# objects buttons
object_progress = Text(f"Obect: 0 / 0")
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
tag_inputs = [InputTag(tag_meta) for tag_meta in g.tag_metas]
for tag_input in tag_inputs:
    tag_input.hide()
disclaimer = NotificationBox(
    title="Warning",
    description="Objects will be modified in-place!",
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
    if len(g.objects) == 0:
        object_id = None
    else:
        object = g.objects[g.current_object_idx]
        object_id = object.to_json()["id"]
    image = g.images[g.current_image_idx]
    image_url = image.preview_url
    image_id = image.id
    show_ann = g.current_annotation.clone(labels=g.objects)
    
    labeled_image.set(
        title=f"{image.name}",
        image_url=image_url,
        ann=show_ann,
        image_id=image_id,
        zoom_to=object_id,
        zoom_factor=g.zoom_factor,
    )

def render_tags():
    if len(g.objects) == 0:
        for ti in tag_inputs:
            ti.hide()
        success_message.hide()
        return

    object = g.objects[g.current_object_idx]
    object_class = object.obj_class

    for i, tm in enumerate(g.tag_metas):
        if tm.applicable_to == sly.TagApplicableTo.OBJECTS_ONLY:
            if len(tm.applicable_classes) == 0 or object_class.name in tm.applicable_classes:
                tag_inputs[i].show()
            else:
                tag_inputs[i].hide()
        else:
            tag_inputs[i].show()
        tag = object.tags.get(tm.name)
        tag_inputs[i].set(tag=tag)

    success_message.hide()

def render_selected_object():
    if len(g.objects) == 0:
        object_number = 0
    else:
        object_number = g.current_object_idx + 1
    object_progress.set(
        f"Object: {object_number} / {g.total_objectss}", status="text"
    )
    render_image()
    render_tags()

def render_selected_image():
    if len(g.images) == 0:
        return  
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
    if g.total_objectss == 0:
        return
    if len([ti for ti in tag_inputs if not ti.is_hidden()]) == 0:
        return

    updated_tags = sly.TagCollection()
    for tag_input in tag_inputs:
        tag = tag_input.get_tag()
        if tag is not None:
            updated_tags = updated_tags.add(tag)
    
    current_label = g.objects[g.current_object_idx]
    for i, label in enumerate(g.current_annotation.labels):
        if label == current_label:
            labels_after_current = g.current_annotation.labels[i+1:]
    g.current_annotation = g.current_annotation.delete_label(current_label)
    for label in labels_after_current:
        g.current_annotation = g.current_annotation.delete_label(label)
    g.current_annotation = g.current_annotation.add_label(
        current_label.clone(tags=updated_tags)
    )
    g.current_annotation = g.current_annotation.add_labels(labels_after_current)
    image_id = g.images[g.current_image_idx].id
    g.api.annotation.upload_ann(image_id, g.current_annotation)
    g.objects = g.filter_labels(g.current_annotation.labels)
    render_tags()
    success_message.show()

@next_object_btn.click
def next_object():
    if g.current_object_idx >= g.total_objectss - 1:
        return
    select_object(g.current_object_idx + 1)

@prev_object_btn.click
def prev_object():
    if g.current_object_idx <= 0:
        return
    select_object(g.current_object_idx - 1)

@next_image_button.click
def next_image():
    if g.current_image_idx >= g.total_images - 1:
        return
    select_image(g.current_image_idx + 1)

@prev_image_button.click
def prev_image():
    if g.current_image_idx <= 0:
        return
    select_image(g.current_image_idx - 1)
