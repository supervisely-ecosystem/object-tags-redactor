import supervisely as sly
from supervisely.app.widgets import Container
import src.globals as g
import src.ui as ui


layout = Container(
    widgets=[
        ui.thumbnail_card,
        ui.classes_selector_card,
        ui.object_selector_card,
        ui.main_window,
    ]
)

app = sly.Application(layout=layout)
ui.select_image(g.current_image_idx)
ui.update_pbar(len(g.completed_images))
ui.load_templates()
