import os
import sys
import tempfile

from send2trash import send2trash
from pypdf import PdfReader, PdfWriter

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QMessageBox,
    QAbstractItemView,
    QFrame,
    QProgressBar,
    QFileDialog,
)

MAX_FILES = 25


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
            self.ui_cfg["ROW_MARGIN_H"],
            self.ui_cfg["ROW_MARGIN_V"],
            self.ui_cfg["ROW_MARGIN_H"],
            self.ui_cfg["ROW_MARGIN_V"],
        )
        layout.setSpacing(self.ui_cfg["ROW_SPACING"])

        self.label = QLabel(f"{row_number}. {file_name}")
        self.label.setStyleSheet(
            f"font-size: {self.ui_cfg['FILE_NAME_FONT_SIZE']}px;"
        )
        layout.addWidget(self.label)

        layout.addStretch()

        self.delete_button = QPushButton("删除")
        self.delete_button.setObjectName("deleteButton")
        self.delete_button.setFixedSize(
            self.ui_cfg["DELETE_BUTTON_WIDTH"],
            self.ui_cfg["DELETE_BUTTON_HEIGHT"],
        )
        self.delete_button.setCursor(Qt.PointingHandCursor)
        self.delete_button.clicked.connect(self.delete_callback)
        self.delete_button.hide()
        layout.addWidget(self.delete_button)

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
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(18)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSpacing(self.ui_cfg["LIST_ITEM_SPACING"])

    def dropEvent(self, event):
        if self.parent_window.is_merging:
            event.ignore()
            return

        super().dropEvent(event)
        self.parent_window.sync_files_from_list()


class PdfMergeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_files = []
        self.is_merging = False
        self.init_ui()

    def init_ui(self):
        self.ui_cfg = {
            "WINDOW_WIDTH": 400,
            "WINDOW_HEIGHT": 700,
            "WINDOW_MIN_WIDTH": 360,
            "WINDOW_MIN_HEIGHT": 520,

            "FONT_SIZE_NORMAL": 14,
            "FILE_NAME_FONT_SIZE": 12,
            "DELETE_BUTTON_FONT_SIZE": 12,

            "MAIN_MARGIN": 18,
            "MAIN_SPACING": 12,
            "OUTPUT_SPACING": 10,
            "BUTTON_SPACING": 12,

            "ROW_MARGIN_H": 10,
            "ROW_MARGIN_V": 6,
            "ROW_SPACING": 8,
            "FILE_ITEM_HEIGHT": 30,
            "LIST_ITEM_SPACING": 3,

            "LIST_BORDER_WIDTH": 1,
            "LIST_BORDER_RADIUS": 10,
            "LIST_PADDING": 8,

            "INPUT_BORDER_RADIUS": 8,
            "INPUT_PADDING": 8,

            "BUTTON_BORDER_RADIUS": 8,
            "BUTTON_PADDING_V": 10,
            "BUTTON_PADDING_H": 18,
            "BUTTON_MIN_HEIGHT": 20,
            "BUTTON_PRESS_TOP": 11,
            "BUTTON_PRESS_BOTTOM": 9,
            "ACTION_BUTTON_WIDTH": 150,
            "ACTION_BUTTON_HEIGHT": 36,
            "BROWSE_BUTTON_WIDTH": 90,

            "PROGRESS_BAR_HEIGHT": 24,

            "DELETE_BUTTON_WIDTH": 40,
            "DELETE_BUTTON_HEIGHT": 30,

            "LIST_BORDER_COLOR": "rgba(255,255,255,0.15)",
            "ROW_HOVER_COLOR": "rgba(255,255,255,0.06)",

            "BUTTON_BG_COLOR": "#3f434a",
            "BUTTON_HOVER_COLOR": "#4b5058",
            "BUTTON_PRESS_COLOR": "#32363d",
            "BUTTON_BORDER_COLOR": "#666b73",
            "BUTTON_TEXT_COLOR": "#f3f4f6",

            "DELETE_BUTTON_BG_COLOR": "#484d55",
            "DELETE_BUTTON_HOVER_COLOR": "#565c65",
            "DELETE_BUTTON_PRESS_COLOR": "#393e46",
            "DELETE_BUTTON_BORDER_COLOR": "#6c727b",
            "DELETE_BUTTON_TEXT_COLOR": "#f3f4f6",
        }

        self.setWindowTitle("PDF 拼接")
        self.resize(
            self.ui_cfg["WINDOW_WIDTH"],
            self.ui_cfg["WINDOW_HEIGHT"],
        )
        self.setMinimumSize(
            self.ui_cfg["WINDOW_MIN_WIDTH"],
            self.ui_cfg["WINDOW_MIN_HEIGHT"],
        )
        self.setAcceptDrops(True)

        self.setStyleSheet(f"""
            QWidget {{
                font-size: {self.ui_cfg["FONT_SIZE_NORMAL"]}px;
            }}

            QListWidget {{
                border: {self.ui_cfg["LIST_BORDER_WIDTH"]}px solid {self.ui_cfg["LIST_BORDER_COLOR"]};
                border-radius: {self.ui_cfg["LIST_BORDER_RADIUS"]}px;
                padding: {self.ui_cfg["LIST_PADDING"]}px;
            }}

            QFrame#fileRow {{
                border-radius: {self.ui_cfg["INPUT_BORDER_RADIUS"]}px;
                background: transparent;
            }}

            QFrame#fileRow:hover {{
                background: {self.ui_cfg["ROW_HOVER_COLOR"]};
            }}

            QLineEdit {{
                padding: {self.ui_cfg["INPUT_PADDING"]}px;
                border-radius: {self.ui_cfg["INPUT_BORDER_RADIUS"]}px;
                font-size: {self.ui_cfg["FONT_SIZE_NORMAL"]}px;
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
                padding: {self.ui_cfg["BUTTON_PADDING_V"]}px {self.ui_cfg["BUTTON_PADDING_H"]}px;
                border-radius: {self.ui_cfg["BUTTON_BORDER_RADIUS"]}px;
                font-size: {self.ui_cfg["FONT_SIZE_NORMAL"]}px;
                min-height: {self.ui_cfg["BUTTON_MIN_HEIGHT"]}px;
                background: {self.ui_cfg["BUTTON_BG_COLOR"]};
                border: 1px solid {self.ui_cfg["BUTTON_BORDER_COLOR"]};
                color: {self.ui_cfg["BUTTON_TEXT_COLOR"]};
            }}

            QPushButton:hover {{
                background: {self.ui_cfg["BUTTON_HOVER_COLOR"]};
            }}

            QPushButton:pressed {{
                background: {self.ui_cfg["BUTTON_PRESS_COLOR"]};
                padding-top: {self.ui_cfg["BUTTON_PRESS_TOP"]}px;
                padding-bottom: {self.ui_cfg["BUTTON_PRESS_BOTTOM"]}px;
            }}

            QPushButton#deleteButton {{
                font-size: {self.ui_cfg["DELETE_BUTTON_FONT_SIZE"]}px;
                background: {self.ui_cfg["DELETE_BUTTON_BG_COLOR"]};
                border: 1px solid {self.ui_cfg["DELETE_BUTTON_BORDER_COLOR"]};
                color: {self.ui_cfg["DELETE_BUTTON_TEXT_COLOR"]};
                border-radius: {self.ui_cfg["BUTTON_BORDER_RADIUS"]}px;
                padding: 0px;
            }}

            QPushButton#deleteButton:hover {{
                background: {self.ui_cfg["DELETE_BUTTON_HOVER_COLOR"]};
            }}

            QPushButton#deleteButton:pressed {{
                background: {self.ui_cfg["DELETE_BUTTON_PRESS_COLOR"]};
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            self.ui_cfg["MAIN_MARGIN"],
            self.ui_cfg["MAIN_MARGIN"],
            self.ui_cfg["MAIN_MARGIN"],
            self.ui_cfg["MAIN_MARGIN"],
        )
        main_layout.setSpacing(self.ui_cfg["MAIN_SPACING"])

        tip_label = QLabel(
            "拖入 1~25 个 PDF；按列表顺序拼接；允许同一文件重复加入；支持拖动调整顺序"
        )
        tip_label.setWordWrap(True)
        main_layout.addWidget(tip_label)

        title_label = QLabel("预选文件列表（支持拖拽追加 / 行内删除 / 拖动排序）")
        title_label.setWordWrap(True)
        main_layout.addWidget(title_label)

        self.file_list = PdfListWidget(self, self.ui_cfg)
        main_layout.addWidget(self.file_list, 1)

        output_layout = QHBoxLayout()
        output_layout.setSpacing(self.ui_cfg["OUTPUT_SPACING"])

        output_label = QLabel("输出文件：")
        default_output_path = os.path.abspath(os.path.join(os.getcwd(), "merged.pdf"))
        self.output_entry = QLineEdit(default_output_path)
        self.output_entry.setToolTip("可输入完整输出路径，或点击“选择位置”")

        self.browse_button = QPushButton("选择位置")
        self.browse_button.setFixedWidth(self.ui_cfg["BROWSE_BUTTON_WIDTH"])
        self.browse_button.clicked.connect(self.choose_output_path)

        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_entry, 1)
        output_layout.addWidget(self.browse_button)
        main_layout.addLayout(output_layout)

        self.delete_checkbox = QCheckBox("拼接完成后将原文件移入回收站")
        self.delete_checkbox.setChecked(False)
        main_layout.addWidget(self.delete_checkbox)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("拼接进度：%p%")
        self.progress_bar.setFixedHeight(self.ui_cfg["PROGRESS_BAR_HEIGHT"])
        main_layout.addWidget(self.progress_bar)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(self.ui_cfg["BUTTON_SPACING"])

        self.run_button = QPushButton("执行拼接")
        self.run_button.setFixedSize(
            self.ui_cfg["ACTION_BUTTON_WIDTH"],
            self.ui_cfg["ACTION_BUTTON_HEIGHT"],
        )
        self.run_button.clicked.connect(self.run_merge)
        button_layout.addWidget(self.run_button)

        self.clear_button = QPushButton("清空全部")
        self.clear_button.setFixedSize(
            self.ui_cfg["ACTION_BUTTON_WIDTH"],
            self.ui_cfg["ACTION_BUTTON_HEIGHT"],
        )
        self.clear_button.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_button)

        main_layout.addLayout(button_layout)

    @staticmethod
    def normalize_path(path):
        """用于比较路径：统一为绝对路径、解析符号链接并处理 Windows 大小写。"""
        return os.path.normcase(os.path.realpath(os.path.abspath(os.path.expanduser(path))))

    @classmethod
    def paths_refer_to_same_file(cls, path_a, path_b):
        """同时处理大小写差异、符号链接和已有文件的硬链接情况。"""
        if cls.normalize_path(path_a) == cls.normalize_path(path_b):
            return True

        try:
            return os.path.exists(path_a) and os.path.exists(path_b) and os.path.samefile(
                path_a, path_b
            )
        except OSError:
            return False

    @staticmethod
    def ensure_pdf_suffix(path):
        path = path.strip()
        if path and not path.lower().endswith(".pdf"):
            path += ".pdf"
        return path

    def choose_output_path(self):
        current_path = self.output_entry.text().strip()
        if not current_path:
            current_path = os.path.join(os.getcwd(), "merged.pdf")
        elif not os.path.isabs(os.path.expanduser(current_path)):
            current_path = os.path.abspath(os.path.expanduser(current_path))

        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "选择输出 PDF 文件的位置",
            current_path,
            "PDF 文件 (*.pdf)",
        )

        if selected_path:
            self.output_entry.setText(os.path.abspath(self.ensure_pdf_suffix(selected_path)))

    def dragEnterEvent(self, event: QDragEnterEvent):
        if self.is_merging:
            event.ignore()
            return

        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        if self.is_merging:
            event.ignore()
            return

        files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = url.toLocalFile()
                if path.lower().endswith(".pdf"):
                    files.append(path)

        if not files:
            event.ignore()
            return

        remaining = MAX_FILES - len(self.selected_files)
        if remaining <= 0:
            QMessageBox.warning(self, "提示", f"最多只能添加 {MAX_FILES} 个 PDF 文件")
            event.ignore()
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
            self.ui_cfg["DELETE_BUTTON_HEIGHT"] + self.ui_cfg["ROW_MARGIN_V"] * 2,
        )

        for i, path in enumerate(self.selected_files, 1):
            item = QListWidgetItem()
            item.setData(Qt.UserRole, path)
            item.setSizeHint(QSize(100, actual_item_height))

            row_widget = FileRowWidget(
                self,
                os.path.basename(path),
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
        if self.is_merging:
            return

        row = self.file_list.row(item)
        if row >= 0:
            del self.selected_files[row]
            self.refresh_list()

    def sync_files_from_list(self):
        if self.is_merging:
            return

        self.selected_files = [
            self.file_list.item(i).data(Qt.UserRole)
            for i in range(self.file_list.count())
        ]
        self.refresh_list()

    def clear_all(self):
        if self.is_merging:
            return

        self.selected_files.clear()
        self.refresh_list()

    def set_merging_state(self, is_merging):
        """拼接期间冻结一切可能改变输入、输出或删除选项的控件。"""
        self.is_merging = is_merging
        enabled = not is_merging

        self.file_list.setEnabled(enabled)
        self.output_entry.setEnabled(enabled)
        self.browse_button.setEnabled(enabled)
        self.delete_checkbox.setEnabled(enabled)
        self.run_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)

        if is_merging:
            self.progress_bar.setFormat("正在拼接：%p%")
        else:
            self.progress_bar.setFormat("拼接进度：%p%")

    def get_output_path(self):
        raw_path = self.ensure_pdf_suffix(self.output_entry.text())
        if not raw_path:
            QMessageBox.critical(self, "错误", "请选择或输入输出 PDF 文件的位置")
            return None

        output_path = os.path.abspath(os.path.expanduser(raw_path))
        output_dir = os.path.dirname(output_path)

        if not os.path.isdir(output_dir):
            QMessageBox.critical(self, "错误", f"输出目录不存在：\n{output_dir}")
            return None

        self.output_entry.setText(output_path)
        return output_path

    def find_output_conflicts(self, file_paths, output_path):
        """返回与输出文件指向同一对象的输入文件，禁止覆盖源文件。"""
        conflicts = []
        seen = set()

        for file_path in file_paths:
            normalized = self.normalize_path(file_path)
            if normalized in seen:
                continue
            seen.add(normalized)

            if self.paths_refer_to_same_file(file_path, output_path):
                conflicts.append(file_path)

        return conflicts

    def preflight_files(self, file_paths):
        """在真正写入前验证全部输入文件，并计算总页数。"""
        total_pages = 0
        invalid_files = []
        encrypted_files = []

        for index, pdf_path in enumerate(file_paths, 1):
            display_name = f"{index}. {pdf_path}"

            if not os.path.isfile(pdf_path):
                invalid_files.append(f"{display_name}\n文件不存在或不是普通文件")
                continue

            if not os.access(pdf_path, os.R_OK):
                invalid_files.append(f"{display_name}\n没有读取权限")
                continue

            try:
                with open(pdf_path, "rb") as source_file:
                    reader = PdfReader(source_file, strict=False)

                    if reader.is_encrypted:
                        encrypted_files.append(display_name)
                        continue

                    page_count = len(reader.pages)
                    if page_count <= 0:
                        invalid_files.append(f"{display_name}\nPDF 中没有可拼接的页面")
                        continue

                    total_pages += page_count

            except Exception as error:
                invalid_files.append(f"{display_name}\n读取失败：{error}")

        if encrypted_files or invalid_files:
            sections = []

            if encrypted_files:
                sections.append(
                    "以下 PDF 已加密，当前版本不支持输入密码，无法拼接：\n"
                    + "\n".join(encrypted_files)
                )

            if invalid_files:
                sections.append(
                    "以下文件无法作为可读 PDF 使用：\n"
                    + "\n\n".join(invalid_files)
                )

            QMessageBox.critical(self, "无法开始拼接", "\n\n".join(sections))
            return None

        return total_pages

    @staticmethod
    def create_temp_output_path(output_path):
        """在输出目录创建临时文件，保证最终 os.replace 可以原子替换。"""
        output_dir = os.path.dirname(output_path)
        output_name = os.path.basename(output_path)
        file_descriptor, temp_path = tempfile.mkstemp(
            prefix=f".{output_name}.",
            suffix=".tmp.pdf",
            dir=output_dir,
        )
        os.close(file_descriptor)
        return temp_path

    def update_progress(self, finished_pages, total_pages):
        # 保留最后 1%，直到临时文件验证并替换为最终输出文件后才显示 100%。
        progress = min(99, int(finished_pages / total_pages * 99))
        self.progress_bar.setValue(progress)
        QApplication.processEvents()

    def merge_pdfs(self, file_paths, output_path, total_pages, delete_source_files):
        """
        先写到同目录临时文件，验证成功后原子替换输出文件；
        只有输出文件已安全生成后，才尝试将源文件移入回收站。

        注意：pypdf 对部分 PDF 采用延迟读取（lazy loading）。
        因此输入文件句柄必须一直保持打开，直到 writer.write() 完成。
        """
        writer = PdfWriter()
        temp_path = None
        source_handles = []
        readers = []

        try:
            temp_path = self.create_temp_output_path(output_path)
            finished_pages = 0
            self.progress_bar.setValue(0)
            QApplication.processEvents()

            for pdf_path in file_paths:
                try:
                    # 不使用 with：writer.write() 时，pypdf 仍可能回头读取源 PDF 的对象流。
                    source_file = open(pdf_path, "rb")
                    source_handles.append(source_file)

                    reader = PdfReader(source_file, strict=False)
                    readers.append(reader)  # 保持 PdfReader 对象存活，直至最终写入完成。

                    if reader.is_encrypted:
                        raise RuntimeError("文件在预检后变为加密状态")

                    for page in reader.pages:
                        writer.add_page(page)
                        finished_pages += 1
                        self.update_progress(finished_pages, total_pages)

                except Exception as error:
                    raise RuntimeError(
                        f"读取或处理文件失败：\n{pdf_path}\n\n{error}"
                    ) from error

            try:
                with open(temp_path, "wb") as output_file:
                    writer.write(output_file)
            except Exception as error:
                raise RuntimeError(f"无法写入临时输出文件：\n{error}") from error

            # 写完后再次读取临时文件，确认其至少能正常打开且页数符合预期。
            try:
                with open(temp_path, "rb") as temp_file:
                    check_reader = PdfReader(temp_file, strict=False)
                    output_page_count = len(check_reader.pages)

                if output_page_count != finished_pages:
                    raise RuntimeError(
                        f"临时输出文件页数异常：期望 {finished_pages} 页，实际 {output_page_count} 页"
                    )
            except Exception as error:
                raise RuntimeError(f"临时输出文件验证失败：\n{error}") from error

            try:
                os.replace(temp_path, output_path)
                temp_path = None
            except Exception as error:
                raise RuntimeError(
                    f"无法替换最终输出文件：\n{output_path}\n\n{error}"
                ) from error

            self.progress_bar.setValue(100)
            QApplication.processEvents()

            moved_to_trash_count = 0
            delete_failures = []

            if delete_source_files:
                seen_sources = set()

                for source_path in file_paths:
                    normalized_source = self.normalize_path(source_path)
                    if normalized_source in seen_sources:
                        continue
                    seen_sources.add(normalized_source)

                    # 双重保护：即使前面的冲突检查被外部文件变化绕过，也绝不处理输出文件。
                    if self.paths_refer_to_same_file(source_path, output_path):
                        continue

                    try:
                        if not os.path.exists(source_path):
                            raise FileNotFoundError("文件在拼接完成前已不存在")

                        send2trash(source_path)
                        moved_to_trash_count += 1

                    except Exception as error:
                        delete_failures.append((source_path, str(error)))

            return moved_to_trash_count, delete_failures

        finally:
            # 输入 PDF 必须在 writer.write() 完成后才可关闭。
            for source_file in source_handles:
                try:
                    source_file.close()
                except OSError:
                    pass

            # 任意失败都只清理临时文件；最终输出文件和源文件均保持原状。
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def confirm_overwrite_if_needed(self, output_path):
        if not os.path.exists(output_path):
            return True

        answer = QMessageBox.question(
            self,
            "确认覆盖",
            f"以下输出文件已经存在：\n{output_path}\n\n是否覆盖它？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def confirm_move_sources_to_trash(self, file_paths):
        unique_files = []
        seen = set()

        for file_path in file_paths:
            normalized = self.normalize_path(file_path)
            if normalized not in seen:
                seen.add(normalized)
                unique_files.append(file_path)

        preview = "\n".join(unique_files[:5])
        if len(unique_files) > 5:
            preview += f"\n……其余 {len(unique_files) - 5} 个文件"

        answer = QMessageBox.warning(
            self,
            "确认移入回收站",
            "拼接成功后，以下源文件将被移入系统回收站：\n\n"
            f"{preview}\n\n"
            "此操作发生在输出文件安全生成后。是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def show_merge_result(self, output_path, moved_to_trash_count, delete_failures):
        success_message = f"拼接完成\n输出文件：\n{output_path}"

        if moved_to_trash_count:
            success_message += f"\n\n已移入回收站的源文件：{moved_to_trash_count} 个"

        if not delete_failures:
            QMessageBox.information(self, "完成", success_message)
            return

        failure_lines = "\n".join(
            f"• {path}\n  原因：{reason}" for path, reason in delete_failures
        )
        QMessageBox.warning(
            self,
            "拼接已完成，但部分源文件未能移入回收站",
            f"{success_message}\n\n以下文件仍保留在原位置：\n{failure_lines}",
        )

    def run_merge(self):
        if self.is_merging:
            return

        if not self.selected_files:
            QMessageBox.critical(self, "错误", "请先拖入至少 1 个 PDF 文件")
            return

        # 拼接使用稳定副本，避免 processEvents 期间任何意外改动影响本次任务。
        file_paths = list(self.selected_files)
        output_path = self.get_output_path()
        if output_path is None:
            return

        output_conflicts = self.find_output_conflicts(file_paths, output_path)
        if output_conflicts:
            QMessageBox.critical(
                self,
                "输出路径无效",
                "输出文件不能与任何输入 PDF 指向同一个文件，否则会覆盖源文件。\n\n"
                "冲突文件：\n"
                + "\n".join(output_conflicts),
            )
            return

        total_pages = self.preflight_files(file_paths)
        if total_pages is None:
            return

        if not self.confirm_overwrite_if_needed(output_path):
            return

        delete_source_files = self.delete_checkbox.isChecked()
        if delete_source_files and not self.confirm_move_sources_to_trash(file_paths):
            return

        try:
            self.set_merging_state(True)
            self.progress_bar.setValue(0)

            moved_to_trash_count, delete_failures = self.merge_pdfs(
                file_paths,
                output_path,
                total_pages,
                delete_source_files,
            )

            self.show_merge_result(
                output_path,
                moved_to_trash_count,
                delete_failures,
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "拼接失败",
                "未能生成新的输出文件；原文件没有被移入回收站。\n\n"
                f"详细原因：\n{error}",
            )

        finally:
            self.set_merging_state(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PdfMergeWindow()
    window.show()
    sys.exit(app.exec())
