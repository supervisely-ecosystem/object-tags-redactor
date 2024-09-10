import json
import os
from pathlib import Path
import supervisely as sly
from supervisely.app.content import DataJson
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
    ClassesTable,
    Field,
    InputNumber,
    Flexbox,
    Progress,
    Input,
    Select,
)
import src.globals as g


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


def _is_applicable(tag, label):
    if len(tag.meta.applicable_classes) == 0:
        return True
    if label.obj_class.name in tag.meta.applicable_classes:
        return True
    return False


# thumbnail
thumbnail = None
if g.dataset_id is None:
    thumbnail = ProjectThumbnail(g.project_info)
else:
    thumbnail = DatasetThumbnail(g.project_info, g.dataset_info)
thumbnail_card = Card(title="1️⃣ Input", content=thumbnail)

# classes selector
classes_selector = ClassesTable(project_id=g.project_id)
select_classes_button = Button("Select")
classes_selector_card = Card(
    title="2️⃣ Select Classes",
    description="Select classes of objects you want to modify",
    content=Container(widgets=[classes_selector, select_classes_button]),
)


@select_classes_button.click
def select_classes():
    g.selected_classes = classes_selector.get_selected_classes()
    select_image(g.current_image_idx)


# images buttons
input_image_number = InputNumber(min=1, max=g.total_images, value=g.current_image_idx + 1)
select_image_button = Button("Go", button_size="small")
image_selector = Field(
    title="Go to image",
    content=Flexbox(widgets=[input_image_number, select_image_button]),
)
image_progress = Text(f"Image:  0 / 0")
next_image_button = Button(text="", icon="zmdi zmdi-arrow-right", button_size="mini")
prev_image_button = Button(text="", icon="zmdi zmdi-arrow-left", button_size="mini")
images_buttons = Flexbox(widgets=[prev_image_button, image_progress, next_image_button])

# objects buttons
object_progress = Text(f"Obect: 0 / 0")
next_object_btn = Button(text="", icon="zmdi zmdi-arrow-right", button_size="mini")
prev_object_btn = Button(text="", icon="zmdi zmdi-arrow-left", button_size="mini")
object_buttons = Flexbox(widgets=[prev_object_btn, object_progress, next_object_btn])
total_image_progress = Progress(message="Images progress", hide_on_finish=False)
pbar = total_image_progress(total=g.total_images, message="Images progress")

# object selector card
buttons = Container(
    widgets=[image_selector, images_buttons, object_buttons, total_image_progress]
)
object_selector_card = Card(content=Container(widgets=[buttons]), title="3️⃣ Select Object", description="Select Image and Object using buttons below")

# tags input card
# templates
templates_selector = Select([])


@loading(templates_selector)
def load_templates():
    remote_filepath = Path(g.pr_path).joinpath("templates.json").as_posix()
    exists = g.api.file.exists(g.team_id, remote_filepath)
    if not exists:
        return
    g.api.file.download(g.team_id, remote_filepath, remote_filepath)
    with open(remote_filepath, "r") as file:
        data = json.load(file)
    items = []
    for template_name, template in data.items():
        n_of_tags = len(template)
        items.append(Select.Item(template_name, f"{template_name} ({n_of_tags} tags)"))
    templates_selector.set(items=items)
    if len(items) == 0:
        apply_template_button.disable()
    os.remove(remote_filepath)


save_template_button = Button(
    "Save", button_type="text", icon="zmdi zmdi-save"
)
cancel_create_template_button = Button(
    "Cancel", button_type="text", icon="zmdi zmdi-close"
)
template_name_input = Input(placeholder="Input template name")
create_new_template_button = Button(
    "Create new", button_type="text", icon="zmdi zmdi-plus"
)
apply_template_button = Button(
    "Apply template", icon="zmdi zmdi-check"
)
remove_template_button = Button(
    "Remove", button_type="text", icon="zmdi zmdi-delete"
)

apply_template_flexbox = Flexbox(widgets=[templates_selector, create_new_template_button, remove_template_button])
create_template_flexbox = Flexbox(widgets=[template_name_input, save_template_button, cancel_create_template_button])
create_template_flexbox.hide()
templates_container = Container(
    widgets=[
        apply_template_flexbox,
        create_template_flexbox,
        apply_template_button,
    ]
)
templates_field = Field(
    title="Templates",
    content=templates_container,
    description="Edit and apply predefined tags templates"
)


def get_func(tag_input):
    def activate_on_change(*args):
        tag_input.activate()

    return activate_on_change


# tag inputs
tag_inputs = [InputTag(tag_meta) for tag_meta in g.tag_metas]
for tag_input in tag_inputs:
    tag_input.hide()
    tag_input.value_changed(get_func(tag_input))
disclaimer = NotificationBox(
    title="Warning",
    description="Objects will be modified in-place!",
    box_type="warning",
)
save_button = Button(text="Save tags", icon="zmdi zmdi-save")
success_message = Text("Tags saved!", status="success")
success_message.hide()
save_and_next_button = Button(text="Save and next", icon="zmdi zmdi-save")

save_container = Container(
    widgets=[
        disclaimer,
        Flexbox(widgets=[save_button, save_and_next_button, success_message]),
    ]
)
tags_container = Container(widgets=tag_inputs, gap=15)
tags_field = Field(title="Tags", content=tags_container, description="Edit tags")
tags_card = Card(
    content=Container(
        widgets=[templates_field, tags_field, save_container], gap=40
    ),
    title="4️⃣ Edit object tags",
    description="Edit tags of the selected object"
)


# labeled image card
labeled_image = LabeledImage()
labeled_image_card = Card(content=labeled_image, title="🖼️ Object preview", description="Inspect the select object")

# main window
main_window = Container(
    widgets=[labeled_image_card, tags_card], direction="horizontal", fractions=[1, 1]
)
main_window_card = Card(title="Edit Tags", content=main_window)


def render_image():
    if len(g.objects) == 0:
        object_id = None
        show_labels = []
    else:
        object = g.objects[g.current_object_idx]
        object_id = object.to_json()["id"]
        show_labels = []
        for label in g.current_annotation.labels:
            if (
                object.binding_key is not None
                and label.binding_key == object.binding_key
            ) or label.to_json()["id"] == object_id:
                show_labels.append(label)
    image = g.images[g.current_image_idx]
    image_url = image.preview_url
    image_id = image.id
    show_ann = g.current_annotation.clone(labels=show_labels)
    image_labeling_url = f"{g.api.server_address}/app/images/{g.team_id}/{g.workspace_id}/{g.project_id}/{image.dataset_id}#image-{image.id}"
    labeled_image.set(
        title=f"{image.name}",
        image_url=image_url,
        ann=show_ann,
        image_id=image_id,
        zoom_to=object_id,
        zoom_factor=g.zoom_factor,
        title_url=image_labeling_url,
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
            if (
                len(tm.applicable_classes) == 0
                or object_class.name in tm.applicable_classes
            ):
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
    object_progress.set(f"Object: {object_number} / {g.total_objects}", status="text")
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
    input_image_number.value = g.current_image_idx + 1
    g.set_image()
    render_selected_image()


@loading(tags_card)
@save_button.click
def save_object_tags():
    if g.total_objects == 0:
        return
    if len([ti for ti in tag_inputs if not ti.is_hidden()]) == 0:
        return

    current_label = g.objects[g.current_object_idx]
    updated_tags = sly.TagCollection()
    for tag_input in tag_inputs:
        tag = tag_input.get_tag()
        if tag is not None and _is_applicable(tag, current_label):
            updated_tags = updated_tags.add(tag)

    # this is needed to keep current order of objects
    for i, label in enumerate(g.current_annotation.labels):
        if label == current_label:
            labels_after_current = g.current_annotation.labels[i + 1 :]
            break
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
    save_template("last saved")
    load_templates()
    render_tags()
    success_message.show()


@next_object_btn.click
def next_object():
    if g.current_object_idx >= g.total_objects - 1:
        next_image()
        return
    select_object(g.current_object_idx + 1)


@prev_object_btn.click
def prev_object():
    if g.current_object_idx <= 0:
        prev_image()
        select_object(g.total_objects - 1)
        return
    select_object(g.current_object_idx - 1)


def update_pbar(n):
    pbar.n = n
    pbar.refresh()
    DataJson()[str(total_image_progress.widget_id)]["status"] = None
    DataJson().send_changes()


@next_image_button.click
def next_image():
    if g.current_image_idx >= g.total_images - 1:
        return
    select_image(g.current_image_idx + 1)
    if g.images[g.current_image_idx].id not in g.completed_images:
        g.completed_images.add(g.images[g.current_image_idx].id)
        g.save_images_stat()
        update_pbar(len(g.completed_images))
    

@prev_image_button.click
def prev_image():
    if g.current_image_idx <= 0:
        return
    select_image(g.current_image_idx - 1)


@save_and_next_button.click
def save_tags_and_next_obj():
    save_object_tags()
    next_object()


@select_image_button.click
def go_to_image():
    img_number = input_image_number.get_value() - 1
    select_image(img_number)


def save_template(name: str):
    new_template = {}
    for tag_input in tag_inputs:
        tag = tag_input.get_tag()
        if tag is not None:
            new_template[tag.meta.name] = tag.to_json()
    remote_filepath = Path(g.pr_path).joinpath(f"templates.json").as_posix()
    exists = g.api.file.exists(g.team_id, remote_filepath)
    if exists:
        g.api.file.download(g.team_id, remote_filepath, remote_filepath)
        with open(remote_filepath, "r") as file:
            data = json.load(file)
            data[name] = new_template
    else:
        data = {name: new_template}
    with open(remote_filepath, "w+") as file:
        json.dump(data, file)
    if g.api.file.exists(g.team_id, remote_filepath):
        g.api.file.remove(g.team_id, remote_filepath)
    g.api.file.upload(g.team_id, remote_filepath, remote_filepath if remote_filepath.startswith("/") else "/" + remote_filepath)
    os.remove(remote_filepath)


def remove_template(name: str):
    remote_filepath = Path(g.pr_path).joinpath(f"templates.json").as_posix()
    g.api.file.download(g.team_id, remote_filepath, remote_filepath)
    with open(remote_filepath, "r") as file:
        data = json.load(file)
        data.pop(name, None)
    with open(remote_filepath, "w+") as file:
        json.dump(data, file)
    if g.api.file.exists(g.team_id, remote_filepath):
        g.api.file.remove(g.team_id, remote_filepath)
    g.api.file.upload(g.team_id, remote_filepath, remote_filepath if remote_filepath.startswith("/") else "/" + remote_filepath)
    os.remove(remote_filepath)


@loading(tags_card)
def apply_template(name):
    remote_filepath = Path(g.pr_path).joinpath(f"templates.json").as_posix()
    g.api.file.download(g.team_id, remote_filepath, remote_filepath)
    if not sly.fs.file_exists(remote_filepath):
        from supervisely.app.exceptions import show_dialog
        sly.logger.warn('Error: invalid template selected, showing dialog window.', extra={'file path': remote_filepath})
        show_dialog(title='Error: file not found', description='Please, make sure that the template you have tried to apply exists and try again.', status='warning')
        return
    with open(remote_filepath, "r") as file:
        data = json.load(file)
        for tag_input in tag_inputs:
            tag_name = tag_input.get_tag_meta().name
            if tag_name in data[name].keys():
                tag_json = data[name][tag_name]
                tag = sly.Tag.from_json(tag_json, g.project_meta.tag_metas)
                if _is_applicable(tag, g.objects[g.current_object_idx]):
                    tag_input.set(tag)
            else:
                tag_input.set(None)
    os.remove(remote_filepath)


@create_new_template_button.click
def create_new_template():
    apply_template_flexbox.hide()
    create_template_flexbox.show()

@cancel_create_template_button.click
def cancel_create_new_template():
    apply_template_flexbox.show()
    create_template_flexbox.hide()

@save_template_button.click
@loading(templates_field)
def save_template_click():
    template_name = template_name_input.get_value()
    if template_name == "":
        return
    save_template(template_name)
    cancel_create_new_template()
    load_templates()

@templates_selector.value_changed
def templates_selector_cb(value):
    if value:
        apply_template_button.enable()
    else:
        apply_template_button.disable()

@apply_template_button.click
@loading(templates_field)
def apply_template_click():
    name = templates_selector.get_value()
    apply_template(name)


@remove_template_button.click
@loading(templates_field)
def remove_template_click():
    name = templates_selector.get_value()
    remove_template(name)
    load_templates()
