import os
import sys
from send2trash import send2trash
from pypdf import PdfReader, PdfWriter

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QLineEdit, QPushButton,
    QCheckBox, QMessageBox, QAbstractItemView, QFrame,
    QProgressBar
)

MAX_FILES = 25  # 25 = 最多允许加入 25 个 PDF 文件


class FileRowWidget(QFrame):
    def __init__(self, parent_window, file_name, row_number, delete_callback, ui_cfg):
        super().__init__()
        self.parent_window = parent_window
        self.delete_callback = delete_callback
        self.ui_cfg = ui_cfg

        self.setObjectName("fileRow")
        self.setMouseTracking(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            self.ui_cfg["ROW_MARGIN_H"],  # 左边距像素
            self.ui_cfg["ROW_MARGIN_V"],  # 上边距像素
            self.ui_cfg["ROW_MARGIN_H"],  # 右边距像素
            self.ui_cfg["ROW_MARGIN_V"],  # 下边距像素
        )
        layout.setSpacing(self.ui_cfg["ROW_SPACING"])  # 行内控件之间的水平间距像素

        self.label = QLabel(f"{row_number}. {file_name}")
        self.label.setStyleSheet(
            f"font-size: {self.ui_cfg['FILE_NAME_FONT_SIZE']}px;"  # 文件名文字大小
        )
        layout.addWidget(self.label)

        layout.addStretch()

        self.delete_button = QPushButton("删除")
        self.delete_button.setObjectName("deleteButton")
        self.delete_button.setFixedSize(
            self.ui_cfg["DELETE_BUTTON_WIDTH"],   # 删除按钮宽度像素
            self.ui_cfg["DELETE_BUTTON_HEIGHT"],  # 删除按钮高度像素
        )
        self.delete_button.setCursor(Qt.PointingHandCursor)
        self.delete_button.clicked.connect(self.delete_callback)
        self.delete_button.hide()
        layout.addWidget(self.delete_button)

    def set_row_text(self, file_name, row_number):
        self.label.setText(f"{row_number}. {file_name}")

    def enterEvent(self, event):
        self.delete_button.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.delete_button.hide()
        super().leaveEvent(event)


class PdfListWidget(QListWidget):
    def __init__(self, parent_window, ui_cfg):
        super().__init__()
        self.parent_window = parent_window
        self.ui_cfg = ui_cfg

        self.setAcceptDrops(False)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)  # InternalMove = 允许列表内部拖动重排
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(18)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def dropEvent(self, event):
        super().dropEvent(event)
        self.parent_window.sync_files_from_list()


class PdfMergeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_files = []
        self.init_ui()

    def init_ui(self):
        # ===== 窗口与样式统一参数 =====
        self.ui_cfg = {
            "WINDOW_WIDTH": 400,       # 窗口默认宽度像素
            "WINDOW_HEIGHT": 700,      # 窗口默认高度像素
            "WINDOW_MIN_WIDTH": 360,   # 窗口最小宽度像素
            "WINDOW_MIN_HEIGHT": 520,  # 窗口最小高度像素

            "FONT_SIZE_NORMAL": 14,         # 全局默认文字大小
            "FILE_NAME_FONT_SIZE": 12,      # 文件列表里文件名文字大小
            "DELETE_BUTTON_FONT_SIZE": 12,  # 行内“删除”按钮文字大小，单独拆出

            "MAIN_MARGIN": 18,      # 主布局四周留白像素
            "MAIN_SPACING": 12,     # 主布局各模块之间的垂直间距像素
            "OUTPUT_SPACING": 10,   # “输出文件名”标签与输入框之间的水平间距像素
            "BUTTON_SPACING": 12,   # 底部按钮之间的水平间距像素

            "ROW_MARGIN_H": 10,     # 每个文件行左右内边距像素
            "ROW_MARGIN_V": 6,      # 每个文件行上下内边距像素
            "ROW_SPACING": 8,       # 文件行内部控件之间的间距像素
            "FILE_ITEM_HEIGHT": 30, # 每个文件行的基础高度像素
            "LIST_ITEM_SPACING": 3, # 文件行与文件行之间的垂直间距像素

            "LIST_BORDER_WIDTH": 1,   # 文件列表边框粗细像素
            "LIST_BORDER_RADIUS": 10, # 文件列表圆角像素
            "LIST_PADDING": 8,        # 文件列表内部留白像素

            "INPUT_BORDER_RADIUS": 8, # 输入框圆角像素
            "INPUT_PADDING": 8,       # 输入框四周内边距像素

            "BUTTON_BORDER_RADIUS": 8,   # 按钮圆角像素
            "BUTTON_PADDING_V": 10,      # 按钮上下内边距像素
            "BUTTON_PADDING_H": 18,      # 按钮左右内边距像素
            "BUTTON_MIN_HEIGHT": 20,     # 按钮最小高度像素
            "BUTTON_PRESS_TOP": 11,      # 按下按钮时上内边距像素，用于制造“下沉感”
            "BUTTON_PRESS_BOTTOM": 9,    # 按下按钮时下内边距像素，用于制造“下沉感”
            "ACTION_BUTTON_WIDTH": 150,  # 底部“执行拼接/清空全部”按钮固定宽度像素
            "ACTION_BUTTON_HEIGHT": 36,  # 底部“执行拼接/清空全部”按钮固定高度像素

            "PROGRESS_BAR_HEIGHT": 24,  # 拼接进度条高度像素

            "DELETE_BUTTON_WIDTH": 40,   # 行内“删除”按钮宽度像素
            "DELETE_BUTTON_HEIGHT": 30,  # 行内“删除”按钮高度像素

            "LIST_BORDER_COLOR": "rgba(255,255,255,0.15)",  # 文件列表边框颜色：白色 15% 透明度
            "ROW_HOVER_COLOR": "rgba(255,255,255,0.06)",    # 鼠标移到文件行上时的高亮颜色：白色 6% 透明度

            "BUTTON_BG_COLOR": "#3f434a",         # 普通按钮默认背景色：灰色
            "BUTTON_HOVER_COLOR": "#4b5058",      # 普通按钮悬停背景色：更亮一点的灰色
            "BUTTON_PRESS_COLOR": "#32363d",      # 普通按钮按下背景色：更深的灰色
            "BUTTON_BORDER_COLOR": "#666b73",     # 普通按钮边框颜色：中灰色
            "BUTTON_TEXT_COLOR": "#f3f4f6",       # 按钮文字颜色：浅灰白

            "DELETE_BUTTON_BG_COLOR": "#484d55",      # 行内删除按钮默认背景色：灰色
            "DELETE_BUTTON_HOVER_COLOR": "#565c65",   # 行内删除按钮悬停背景色：更亮一点的灰色
            "DELETE_BUTTON_PRESS_COLOR": "#393e46",   # 行内删除按钮按下背景色：更深的灰色
            "DELETE_BUTTON_BORDER_COLOR": "#6c727b",  # 行内删除按钮边框颜色：中灰色
            "DELETE_BUTTON_TEXT_COLOR": "#f3f4f6",    # 行内删除按钮文字颜色：浅灰白
        }

        self.setWindowTitle("PDF 拼接")
        self.resize(
            self.ui_cfg["WINDOW_WIDTH"],   # 窗口默认宽度
            self.ui_cfg["WINDOW_HEIGHT"],  # 窗口默认高度
        )
        self.setMinimumSize(
            self.ui_cfg["WINDOW_MIN_WIDTH"],   # 窗口最小宽度
            self.ui_cfg["WINDOW_MIN_HEIGHT"],  # 窗口最小高度
        )
        self.setAcceptDrops(True)

        self.setStyleSheet(f"""
            QWidget {{
                font-size: {self.ui_cfg["FONT_SIZE_NORMAL"]}px;   /* 全局默认文字大小 */
            }}

            QListWidget {{
                border: {self.ui_cfg["LIST_BORDER_WIDTH"]}px solid {self.ui_cfg["LIST_BORDER_COLOR"]}; /* 列表边框粗细与颜色 */
                border-radius: {self.ui_cfg["LIST_BORDER_RADIUS"]}px;  /* 列表圆角大小 */
                padding: {self.ui_cfg["LIST_PADDING"]}px;              /* 列表内部留白 */
            }}

            QFrame#fileRow {{
                border-radius: {self.ui_cfg["INPUT_BORDER_RADIUS"]}px; /* 文件行圆角 */
                background: transparent;                               /* 默认透明背景 */
            }}

            QFrame#fileRow:hover {{
                background: {self.ui_cfg["ROW_HOVER_COLOR"]};          /* 文件行悬停高亮颜色 */
            }}

            QLineEdit {{
                padding: {self.ui_cfg["INPUT_PADDING"]}px;             /* 输入框四周内边距 */
                border-radius: {self.ui_cfg["INPUT_BORDER_RADIUS"]}px; /* 输入框圆角大小 */
                font-size: {self.ui_cfg["FONT_SIZE_NORMAL"]}px;        /* 输入框文字大小 */
            }}

            QProgressBar {{
                border: 1px solid {self.ui_cfg["BUTTON_BORDER_COLOR"]};
                border-radius: {self.ui_cfg["INPUT_BORDER_RADIUS"]}px;
                text-align: center;
                height: {self.ui_cfg["PROGRESS_BAR_HEIGHT"]}px;
                color: {self.ui_cfg["BUTTON_TEXT_COLOR"]};
            }}

            QProgressBar::chunk {{
                border-radius: {self.ui_cfg["INPUT_BORDER_RADIUS"]}px;
                background: {self.ui_cfg["BUTTON_HOVER_COLOR"]};
            }}

            QPushButton {{
                padding: {self.ui_cfg["BUTTON_PADDING_V"]}px {self.ui_cfg["BUTTON_PADDING_H"]}px; /* 按钮上下/左右内边距 */
                border-radius: {self.ui_cfg["BUTTON_BORDER_RADIUS"]}px;                             /* 按钮圆角大小 */
                font-size: {self.ui_cfg["FONT_SIZE_NORMAL"]}px;                                     /* 按钮文字大小 */
                min-height: {self.ui_cfg["BUTTON_MIN_HEIGHT"]}px;                                  /* 按钮最小高度 */
                background: {self.ui_cfg["BUTTON_BG_COLOR"]};                                      /* 普通按钮默认背景色 */
                border: 1px solid {self.ui_cfg["BUTTON_BORDER_COLOR"]};                            /* 普通按钮边框粗细与颜色，形成实体轮廓 */
                color: {self.ui_cfg["BUTTON_TEXT_COLOR"]};                                         /* 普通按钮文字颜色 */
            }}

            QPushButton:hover {{
                background: {self.ui_cfg["BUTTON_HOVER_COLOR"]}; /* 普通按钮悬停背景色 */
            }}

            QPushButton:pressed {{
                background: {self.ui_cfg["BUTTON_PRESS_COLOR"]};          /* 普通按钮按下背景色 */
                padding-top: {self.ui_cfg["BUTTON_PRESS_TOP"]}px;         /* 按下时增加上内边距，制造按钮下沉感 */
                padding-bottom: {self.ui_cfg["BUTTON_PRESS_BOTTOM"]}px;   /* 按下时减少下内边距，制造按钮下沉感 */
            }}

            QPushButton#deleteButton {{
                font-size: {self.ui_cfg["DELETE_BUTTON_FONT_SIZE"]}px;               /* 删除按钮文字大小，单独控制 */
                background: {self.ui_cfg["DELETE_BUTTON_BG_COLOR"]};                 /* 删除按钮默认背景色 */
                border: 1px solid {self.ui_cfg["DELETE_BUTTON_BORDER_COLOR"]};       /* 删除按钮边框，形成实体轮廓 */
                color: {self.ui_cfg["DELETE_BUTTON_TEXT_COLOR"]};                    /* 删除按钮文字颜色 */
                border-radius: {self.ui_cfg["BUTTON_BORDER_RADIUS"]}px;              /* 删除按钮圆角大小 */
                padding: 0px;                                                        /* 删除按钮内部不额外留白 */
            }}

            QPushButton#deleteButton:hover {{
                background: {self.ui_cfg["DELETE_BUTTON_HOVER_COLOR"]}; /* 删除按钮悬停背景色 */
            }}

            QPushButton#deleteButton:pressed {{
                background: {self.ui_cfg["DELETE_BUTTON_PRESS_COLOR"]}; /* 删除按钮按下背景色 */
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            self.ui_cfg["MAIN_MARGIN"],  # 左边留白像素
            self.ui_cfg["MAIN_MARGIN"],  # 上边留白像素
            self.ui_cfg["MAIN_MARGIN"],  # 右边留白像素
            self.ui_cfg["MAIN_MARGIN"],  # 下边留白像素
        )
        main_layout.setSpacing(self.ui_cfg["MAIN_SPACING"])  # 主布局各块之间的垂直间距像素

        tip_label = QLabel("拖入 1~25 个 PDF；按列表顺序拼接；允许同一文件重复加入；支持拖动调整顺序")
        tip_label.setWordWrap(True)
        main_layout.addWidget(tip_label)

        title_label = QLabel("预选文件列表（支持拖拽追加 / 行内删除 / 拖动排序）")
        title_label.setWordWrap(True)
        main_layout.addWidget(title_label)

        self.file_list = PdfListWidget(self, self.ui_cfg)
        main_layout.addWidget(self.file_list, 1)  # 1 = 拉伸因子，表示列表区域优先占据剩余空间

        output_layout = QHBoxLayout()
        output_layout.setSpacing(self.ui_cfg["OUTPUT_SPACING"])  # 输出标签和输入框之间的水平间距像素

        output_label = QLabel("输出文件名：")
        self.output_entry = QLineEdit("merged")
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_entry, 1)  # 1 = 输入框拉伸因子
        main_layout.addLayout(output_layout)

        self.delete_checkbox = QCheckBox("拼接完成后删除原文件")
        self.delete_checkbox.setChecked(False)  # False = 默认关闭删除原文件功能
        main_layout.addWidget(self.delete_checkbox)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("拼接进度：%p%")
        self.progress_bar.setFixedHeight(self.ui_cfg["PROGRESS_BAR_HEIGHT"])
        main_layout.addWidget(self.progress_bar)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(self.ui_cfg["BUTTON_SPACING"])  # 底部按钮之间的水平间距像素

        self.run_button = QPushButton("执行拼接")
        self.run_button.setFixedSize(
            self.ui_cfg["ACTION_BUTTON_WIDTH"],   # 底部按钮固定宽度
            self.ui_cfg["ACTION_BUTTON_HEIGHT"],  # 底部按钮固定高度
        )
        self.run_button.clicked.connect(self.run_merge)
        button_layout.addWidget(self.run_button)

        self.clear_button = QPushButton("清空全部")
        self.clear_button.setFixedSize(
            self.ui_cfg["ACTION_BUTTON_WIDTH"],   # 底部按钮固定宽度
            self.ui_cfg["ACTION_BUTTON_HEIGHT"],  # 底部按钮固定高度
        )
        self.clear_button.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_button)

        main_layout.addLayout(button_layout)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            pdf_found = False
            for url in event.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith(".pdf"):
                    pdf_found = True
                    break
            if pdf_found:
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = url.toLocalFile()
                if path.lower().endswith(".pdf"):
                    files.append(path)

        if not files:
            return

        remaining = MAX_FILES - len(self.selected_files)
        if remaining <= 0:
            QMessageBox.warning(self, "提示", f"最多只能添加 {MAX_FILES} 个 PDF 文件")
            return

        files_to_add = files[:remaining]
        self.selected_files.extend(files_to_add)
        self.refresh_list()

        if len(files) > remaining:
            QMessageBox.warning(self, "提示", f"最多只能添加 {MAX_FILES} 个 PDF 文件，超出的已忽略")

        event.acceptProposedAction()

    def refresh_list(self, keep_scroll=True):
        scroll_bar = self.file_list.verticalScrollBar()
        old_scroll_value = scroll_bar.value()
        old_scroll_max = scroll_bar.maximum()
        was_at_bottom = old_scroll_max > 0 and old_scroll_value >= old_scroll_max - 5

        self.file_list.clear()

        actual_item_height = max(
            self.ui_cfg["FILE_ITEM_HEIGHT"],
            self.ui_cfg["DELETE_BUTTON_HEIGHT"] + self.ui_cfg["ROW_MARGIN_V"] * 2
        )

        for i, path in enumerate(self.selected_files, 1):
            file_name = os.path.basename(path)

            item = QListWidgetItem()
            item.setData(Qt.UserRole, path)
            item.setSizeHint(QSize(
                100,
                actual_item_height
            ))

            row_widget = FileRowWidget(
                self,
                file_name,
                i,
                delete_callback=lambda _, item=item: self.delete_item(item),
                ui_cfg=self.ui_cfg,
            )

            self.file_list.addItem(item)
            self.file_list.setItemWidget(item, row_widget)

        if keep_scroll:
            def restore_scroll():
                new_scroll_bar = self.file_list.verticalScrollBar()

                if was_at_bottom:
                    new_scroll_bar.setValue(new_scroll_bar.maximum())
                else:
                    new_scroll_bar.setValue(
                        min(old_scroll_value, new_scroll_bar.maximum())
                    )

            QTimer.singleShot(0, restore_scroll)

    def delete_item(self, item):
        row = self.file_list.row(item)
        if row >= 0:
            del self.selected_files[row]
            self.refresh_list()

    def sync_files_from_list(self):
        new_files = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            path = item.data(Qt.UserRole)
            new_files.append(path)

        self.selected_files = new_files
        self.refresh_list()

    def clear_all(self):
        self.selected_files.clear()
        self.refresh_list()

    def merge_pdfs(self, file_paths, output_path, delete_source_files):
        writer = PdfWriter()

        total_pages = 0
        for pdf_path in file_paths:
            reader = PdfReader(pdf_path)
            total_pages += len(reader.pages)

        finished_pages = 0
        self.progress_bar.setValue(0)
        QApplication.processEvents()

        for pdf_path in file_paths:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                writer.add_page(page)
                finished_pages += 1

                progress = int(finished_pages / total_pages * 100)
                self.progress_bar.setValue(progress)
                QApplication.processEvents()

        with open(output_path, "wb") as f:
            writer.write(f)

        self.progress_bar.setValue(100)
        QApplication.processEvents()

        if delete_source_files:
            output_abs = os.path.abspath(output_path)
            source_abs_set = {os.path.abspath(path) for path in file_paths}

            for file_path in source_abs_set:
                if file_path != output_abs and os.path.exists(file_path):
                    send2trash(file_path)

    def run_merge(self):
        if not self.selected_files:
            QMessageBox.critical(self, "错误", "请先拖入至少 1 个 PDF 文件")
            return

        output_name = self.output_entry.text().strip()
        if not output_name:
            QMessageBox.critical(self, "错误", "请输入输出文件名")
            return

        if not output_name.lower().endswith(".pdf"):
            output_name += ".pdf"

        try:
            self.run_button.setEnabled(False)
            self.clear_button.setEnabled(False)
            self.progress_bar.setValue(0)

            self.merge_pdfs(
                self.selected_files,
                output_name,
                self.delete_checkbox.isChecked()
            )

            QMessageBox.information(self, "完成", f"拼接完成\n输出文件：{output_name}")

        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

        finally:
            self.run_button.setEnabled(True)
            self.clear_button.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PdfMergeWindow()
    window.show()
    sys.exit(app.exec())