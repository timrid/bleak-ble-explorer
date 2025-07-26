import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW


class CustomListView(toga.ScrollContainer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.container = toga.Box(style=Pack(direction=COLUMN, flex=1))
        self.content = self.container

    def clear(self) -> None:
        self.container.clear()

    def add_row(self, row: "CustomListRow"):
        self.container.add(row)
        self.container.add(toga.Divider())


class CustomListRow(toga.Box):
    def __init__(self):
        super().__init__(style=Pack(direction=ROW, margin=5))
