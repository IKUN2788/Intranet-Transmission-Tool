"""
局域网文件极速传输器
====================
基于 PyQt5 的局域网文件传输工具（单文件版）。

功能：
  - 传输方：选择文件/文件夹，输入接收方 IP，高速发送
  - 接收方：监听端口，自动接收文件到指定目录

传输协议（TCP Socket）：
  [4字节: 文件数量]
  对于每个文件:
    [4字节: 文件名UTF-8字节长度][文件名UTF-8][8字节: 文件大小][文件数据]
"""

import os
import sys
import socket
import struct
import time

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget,
    QListWidget, QListWidgetItem, QLineEdit, QProgressBar,
    QFileDialog, QTextEdit, QSpinBox, QMessageBox, QAbstractItemView,
    QGraphicsDropShadowEffect,
)

# ============================================================================
# 常量
# ============================================================================
CHUNK_SIZE = 1024 * 1024   # 传输块大小 (1MB，局域网高速传输)
DEFAULT_PORT = 8888        # 默认端口

# 主题色
PRIMARY = "#2f80ed"
PRIMARY_HOVER = "#2a72d4"
PRIMARY_PRESSED = "#2563b8"
SUCCESS = "#27ae60"
SUCCESS_HOVER = "#219653"
SUCCESS_PRESSED = "#1e8a4c"
DANGER = "#eb5757"
DANGER_HOVER = "#d94444"
DANGER_PRESSED = "#c43c3c"
BG = "#f5f7fb"
CARD = "#ffffff"
TEXT = "#1f2937"
TEXT_SECONDARY = "#6b7280"
BORDER = "#e5e7eb"
BADGE_BG = "#eaf2fd"


# ============================================================================
# 样式
# ============================================================================
def add_card_shadow(widget, blur=28, y_offset=6, alpha=28):
    """给卡片添加柔和阴影。"""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setXOffset(0)
    shadow.setYOffset(y_offset)
    shadow.setColor(QColor(31, 65, 129, alpha))
    widget.setGraphicsEffect(shadow)
    return shadow


STYLESHEET = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: "Microsoft YaHei", "Segoe UI", "PingFang SC", sans-serif;
    font-size: 14px;
}}

/* ===== 标题 ===== */
#appTitle {{
    font-size: 30px;
    font-weight: bold;
    color: {TEXT};
    letter-spacing: 1px;
}}

#appSubtitle {{
    font-size: 15px;
    color: {TEXT_SECONDARY};
}}

/* ===== 卡片 ===== */
#card {{
    background-color: {CARD};
    border: 1px solid {BORDER};
    border-radius: 16px;
}}

#card:hover {{
    border: 1px solid {PRIMARY};
}}

#cardTitle {{
    font-size: 21px;
    font-weight: bold;
    color: {TEXT};
}}

#cardDesc {{
    font-size: 13px;
    color: {TEXT_SECONDARY};
    line-height: 1.5;
}}

/* ===== 按钮 ===== */
QPushButton {{
    background-color: {PRIMARY};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 11px 24px;
    font-size: 15px;
    font-weight: 500;
    min-height: 20px;
}}
QPushButton:hover {{
    background-color: {PRIMARY_HOVER};
}}
QPushButton:pressed {{
    background-color: {PRIMARY_PRESSED};
}}
QPushButton:disabled {{
    background-color: #cbd5e1;
    color: #94a3b8;
}}

#btnPrimary {{
    background-color: {SUCCESS};
    font-weight: bold;
}}
#btnPrimary:hover {{
    background-color: {SUCCESS_HOVER};
}}
#btnPrimary:pressed {{
    background-color: {SUCCESS_PRESSED};
}}

#btnDanger {{
    background-color: {DANGER};
}}
#btnDanger:hover {{
    background-color: {DANGER_HOVER};
}}
#btnDanger:pressed {{
    background-color: {DANGER_PRESSED};
}}

#btnSecondary {{
    background-color: transparent;
    color: {PRIMARY};
    border: 1px solid {PRIMARY};
}}
#btnSecondary:hover {{
    background-color: {BADGE_BG};
}}
#btnSecondary:pressed {{
    background-color: #dceafc;
}}

/* ===== 输入框 ===== */
QLineEdit, QSpinBox {{
    background-color: white;
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    selection-background-color: {PRIMARY};
}}
QLineEdit:focus, QSpinBox:focus {{
    border: 1px solid {PRIMARY};
}}
QLineEdit:disabled {{
    background-color: #f3f4f6;
    color: #9ca3af;
}}

/* ===== 列表 ===== */
QListWidget {{
    background-color: white;
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px;
}}
QListWidget::item {{
    padding: 8px 10px;
    border-radius: 4px;
}}
QListWidget::item:selected {{
    background-color: {BADGE_BG};
    color: {TEXT};
}}
QListWidget::item:hover {{
    background-color: #f3f6fa;
}}

/* ===== 进度条 ===== */
QProgressBar {{
    background-color: #e8edf3;
    border: none;
    border-radius: 9px;
    text-align: center;
    font-size: 13px;
    font-weight: bold;
    color: {TEXT};
    min-height: 24px;
}}
QProgressBar::chunk {{
    background-color: {SUCCESS};
    border-radius: 9px;
}}

/* ===== 日志文本框 ===== */
QTextEdit {{
    background-color: #1f2937;
    color: #e5e7eb;
    border: none;
    border-radius: 10px;
    padding: 12px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
}}

/* ===== 标签 ===== */
QLabel {{
    background-color: transparent;
}}

#fieldLabel {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
}}

#statusLabel {{
    font-size: 16px;
    font-weight: bold;
    color: {PRIMARY};
}}

#speedLabel {{
    font-size: 13px;
    color: {TEXT_SECONDARY};
}}

#ipBadge {{
    background-color: {BADGE_BG};
    color: {PRIMARY};
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 500;
}}

/* ===== 滚动条 ===== */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #cbd5e1;
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #a0aec0;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: #cbd5e1;
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #a0aec0;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
"""


# ============================================================================
# 传输协议函数
# ============================================================================
def get_local_ip():
    """获取本机局域网 IP 地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def format_size(size_bytes):
    """将字节数格式化为可读字符串"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_speed(speed_bytes):
    """格式化传输速度"""
    if speed_bytes < 1024:
        return f"{speed_bytes:.0f} B/s"
    elif speed_bytes < 1024 * 1024:
        return f"{speed_bytes / 1024:.1f} KB/s"
    elif speed_bytes < 1024 * 1024 * 1024:
        return f"{speed_bytes / (1024 * 1024):.1f} MB/s"
    else:
        return f"{speed_bytes / (1024 * 1024 * 1024):.2f} GB/s"


def send_all(sock, data):
    """确保所有数据都被发送"""
    total_sent = 0
    while total_sent < len(data):
        sent = sock.send(data[total_sent:])
        if sent == 0:
            raise ConnectionError("连接已断开")
        total_sent += sent


def recv_exact(sock, n):
    """精确接收 n 个字节"""
    data = b""
    while len(data) < n:
        chunk = sock.recv(min(n - len(data), CHUNK_SIZE))
        if not chunk:
            raise ConnectionError("连接已断开")
        data += chunk
    return data


def get_unique_path(path):
    """如果文件已存在，生成唯一文件名"""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    counter = 1
    while os.path.exists(f"{base} ({counter}){ext}"):
        counter += 1
    return f"{base} ({counter}){ext}"


def send_files(sock, file_paths, progress_cb=None, cancel_cb=None):
    """
    通过 socket 发送文件列表。
    返回: (成功文件数, 失败文件列表)
    """
    # 收集文件信息
    file_infos = []
    total_bytes = 0
    for path in file_paths:
        if not os.path.isfile(path):
            continue
        size = os.path.getsize(path)
        name = os.path.basename(path)
        file_infos.append((path, name, size))
        total_bytes += size

    actual_count = len(file_infos)
    send_all(sock, struct.pack("!I", actual_count))  # 发送文件数量

    sent_total = 0
    success_count = 0
    failed_files = []

    for idx, (path, name, size) in enumerate(file_infos):
        if cancel_cb and cancel_cb():
            break

        name_bytes = name.encode("utf-8")
        send_all(sock, struct.pack("!I", len(name_bytes)))  # 文件名长度
        send_all(sock, name_bytes)                           # 文件名
        send_all(sock, struct.pack("!Q", size))              # 文件大小

        bytes_sent = 0
        start_time = time.time()
        last_update = start_time

        try:
            with open(path, "rb") as f:
                while bytes_sent < size:
                    if cancel_cb and cancel_cb():
                        break
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    send_all(sock, chunk)
                    bytes_sent += len(chunk)
                    sent_total += len(chunk)

                    now = time.time()
                    if progress_cb and (now - last_update >= 0.1 or bytes_sent == size):
                        total_speed = sent_total / max(now - start_time, 0.001) if now - start_time > 0 else 0
                        progress_cb(idx + 1, actual_count, name, bytes_sent, size,
                                    total_bytes, sent_total, total_speed)
                        last_update = now

            if bytes_sent == size:
                success_count += 1
            else:
                failed_files.append(name)
        except Exception as e:
            failed_files.append(f"{name} ({e})")

    return success_count, failed_files


def receive_files(sock, save_dir, progress_cb=None, cancel_cb=None):
    """
    通过 socket 接收文件。
    返回: (成功文件数, 失败文件列表)
    """
    file_count = struct.unpack("!I", recv_exact(sock, 4))[0]  # 接收文件数量

    success_count = 0
    failed_files = []
    total_received = 0

    for i in range(file_count):
        if cancel_cb and cancel_cb():
            break

        name_len = struct.unpack("!I", recv_exact(sock, 4))[0]  # 文件名长度
        filename = recv_exact(sock, name_len).decode("utf-8")   # 文件名
        filesize = struct.unpack("!Q", recv_exact(sock, 8))[0]  # 文件大小

        save_path = get_unique_path(os.path.join(save_dir, filename))

        bytes_received = 0
        start_time = time.time()
        last_update = start_time

        try:
            with open(save_path, "wb") as f:
                while bytes_received < filesize:
                    if cancel_cb and cancel_cb():
                        break
                    to_read = min(CHUNK_SIZE, filesize - bytes_received)
                    chunk = recv_exact(sock, to_read)
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_received += len(chunk)
                    total_received += len(chunk)

                    now = time.time()
                    if progress_cb and (now - last_update >= 0.1 or bytes_received == filesize):
                        total_speed = total_received / max(now - start_time, 0.001) if now - start_time > 0 else 0
                        progress_cb(i + 1, file_count, filename, bytes_received, filesize, total_speed)
                        last_update = now

            if bytes_received == filesize:
                success_count += 1
            else:
                failed_files.append(filename)
        except Exception as e:
            failed_files.append(f"{filename} ({e})")

    return success_count, failed_files


def resource_path(relative):
    """获取资源路径（兼容 PyInstaller 打包）"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative)


# ============================================================================
# 传输方
# ============================================================================
class SendWorker(QThread):
    """发送文件的线程"""
    progress = pyqtSignal(int, int, str, int, int, int, int, float)
    finished_ok = pyqtSignal(int, list)
    error = pyqtSignal(str)

    def __init__(self, host, port, file_paths):
        super().__init__()
        self.host = host
        self.port = port
        self.file_paths = file_paths
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _cancelled_cb(self):
        return self._cancelled

    def run(self):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.host, self.port))
            sock.settimeout(None)
            success, failed = send_files(
                sock, self.file_paths,
                progress_cb=self.progress.emit,
                cancel_cb=self._cancelled_cb
            )
            self.finished_ok.emit(success, failed)
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))
            else:
                self.finished_ok.emit(0, ["已取消"])
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass


class SenderWindow(QWidget):
    """传输方界面"""
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.worker = None
        self.setAcceptDrops(True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 24)
        layout.setSpacing(16)

        # 顶部栏
        top_bar = QHBoxLayout()
        back_btn = QPushButton("← 返回")
        back_btn.setObjectName("btnSecondary")
        back_btn.setFixedWidth(96)
        back_btn.setFixedHeight(36)
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(back_btn)

        title = QLabel("传输文件")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignCenter)
        top_bar.addWidget(title, 1)

        top_bar.addSpacing(96)
        layout.addLayout(top_bar)

        # 本机 IP 提示
        ip_hint = QLabel(f"本机 IP：{get_local_ip()}")
        ip_hint.setObjectName("ipBadge")
        ip_hint.setAlignment(Qt.AlignCenter)
        ip_hint.setFixedHeight(34)
        layout.addWidget(ip_hint)

        # 文件选择卡片
        file_card = QFrame()
        file_card.setObjectName("card")
        add_card_shadow(file_card)
        file_layout = QVBoxLayout(file_card)
        file_layout.setContentsMargins(20, 18, 20, 18)
        file_layout.setSpacing(12)

        file_header = QHBoxLayout()
        file_title = QLabel("选择要发送的文件")
        file_title.setObjectName("cardTitle")
        file_header.addWidget(file_title)
        file_header.addStretch()

        add_btn = QPushButton("添加文件")
        add_btn.clicked.connect(self._add_files)
        file_header.addWidget(add_btn)

        add_dir_btn = QPushButton("添加文件夹")
        add_dir_btn.clicked.connect(self._add_folder)
        file_header.addWidget(add_dir_btn)

        clear_btn = QPushButton("清空")
        clear_btn.setObjectName("btnSecondary")
        clear_btn.clicked.connect(self._clear_files)
        file_header.addWidget(clear_btn)

        file_layout.addLayout(file_header)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list.setDragDropMode(QAbstractItemView.DropOnly)
        self.file_list.setAcceptDrops(True)
        self.file_list.setMinimumHeight(200)
        file_layout.addWidget(self.file_list)

        self.file_count_label = QLabel("共 0 个文件，总大小 0 B")
        self.file_count_label.setObjectName("fieldLabel")
        file_layout.addWidget(self.file_count_label)

        layout.addWidget(file_card)

        # 接收方地址
        addr_card = QFrame()
        addr_card.setObjectName("card")
        add_card_shadow(addr_card)
        addr_layout = QVBoxLayout(addr_card)
        addr_layout.setContentsMargins(20, 18, 20, 18)
        addr_layout.setSpacing(12)

        addr_title = QLabel("接收方地址")
        addr_title.setObjectName("cardTitle")
        addr_layout.addWidget(addr_title)

        addr_row = QHBoxLayout()
        ip_label = QLabel("IP 地址")
        ip_label.setObjectName("fieldLabel")
        addr_row.addWidget(ip_label)

        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("例如：192.168.1.100")
        addr_row.addWidget(self.ip_edit, 3)

        port_label = QLabel("端口")
        port_label.setObjectName("fieldLabel")
        addr_row.addWidget(port_label)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(DEFAULT_PORT)
        addr_row.addWidget(self.port_spin, 1)

        addr_layout.addLayout(addr_row)
        layout.addWidget(addr_card)

        # 进度与状态
        status_card = QFrame()
        status_card.setObjectName("card")
        add_card_shadow(status_card)
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(20, 18, 20, 18)
        status_layout.setSpacing(12)

        status_row = QHBoxLayout()
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        self.speed_label = QLabel("")
        self.speed_label.setObjectName("speedLabel")
        status_row.addWidget(self.speed_label)
        status_layout.addLayout(status_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        status_layout.addWidget(self.progress_bar)

        layout.addWidget(status_card)

        # 发送按钮
        self.send_btn = QPushButton("开始发送")
        self.send_btn.setObjectName("btnPrimary")
        self.send_btn.setFixedHeight(48)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self._start_send)
        layout.addWidget(self.send_btn)

        # 日志
        log_label = QLabel("传输日志")
        log_label.setObjectName("fieldLabel")
        layout.addWidget(log_label)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(110)
        layout.addWidget(self.log_view)

    # ===== 文件管理 =====
    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择要发送的文件")
        for p in paths:
            self._append_file(p)

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择要发送的文件夹")
        if folder:
            self._append_file(folder)

    def _append_file(self, path):
        for i in range(self.file_list.count()):
            if self.file_list.item(i).data(Qt.UserRole) == path:
                return
        item = QListWidgetItem(os.path.basename(path))
        item.setData(Qt.UserRole, path)
        item.setToolTip(path)
        self.file_list.addItem(item)
        self._update_file_count()

    def _clear_files(self):
        self.file_list.clear()
        self._update_file_count()

    def _update_file_count(self):
        total = 0
        for i in range(self.file_list.count()):
            path = self.file_list.item(i).data(Qt.UserRole)
            if os.path.isfile(path):
                total += os.path.getsize(path)
        self.file_count_label.setText(f"共 {self.file_list.count()} 个文件，总大小 {format_size(total)}")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.exists(path):
                self._append_file(path)
        event.acceptProposedAction()

    # ===== 发送 =====
    def _collect_files(self):
        """收集文件列表，展开文件夹"""
        result = []
        for i in range(self.file_list.count()):
            path = self.file_list.item(i).data(Qt.UserRole)
            if os.path.isfile(path):
                result.append(path)
            elif os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for f in files:
                        result.append(os.path.join(root, f))
        return result

    def _start_send(self):
        if self.worker and self.worker.isRunning():
            return

        files = self._collect_files()
        if not files:
            QMessageBox.warning(self, "提示", "请先选择要发送的文件")
            return

        host = self.ip_edit.text().strip()
        if not host:
            QMessageBox.warning(self, "提示", "请输入接收方 IP 地址")
            return

        port = self.port_spin.value()
        self._log(f"准备发送 {len(files)} 个文件到 {host}:{port}")

        self.send_btn.setText("发送中...")
        self.send_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在连接...")
        self.speed_label.setText("")

        self.worker = SendWorker(host, port, files)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, cur, count, name, cur_size, total_size, total_all, sent_all, speed):
        pct = int(sent_all / total_all * 100) if total_all > 0 else 0
        self.progress_bar.setValue(pct)
        self.progress_bar.setFormat(f"{pct}%  ({cur}/{count})")
        self.status_label.setText(f"正在发送：{name}")
        self.speed_label.setText(
            f"{format_size(cur_size)} / {format_size(total_size)}  ·  {format_speed(speed)}"
        )

    def _on_finished(self, success, failed):
        self.send_btn.setText("开始发送")
        self.send_btn.setEnabled(True)
        self.progress_bar.setValue(100 if not failed else self.progress_bar.value())
        self.progress_bar.setFormat("完成")
        self.status_label.setText(f"传输完成：成功 {success} 个，失败 {len(failed)} 个")
        self.speed_label.setText("")
        for f in failed:
            self._log(f"[失败] {f}")
        self._log(f"发送完成：成功 {success} 个，失败 {len(failed)} 个")
        self.worker = None

    def _on_error(self, msg):
        self.send_btn.setText("开始发送")
        self.send_btn.setEnabled(True)
        self.progress_bar.setFormat("失败")
        self.status_label.setText("发送失败")
        self.speed_label.setText("")
        self._log(f"[错误] {msg}")
        QMessageBox.critical(self, "发送失败", f"无法连接到接收方或传输出错：\n{msg}")
        self.worker = None

    def _log(self, msg):
        self.log_view.append(f"[{time.strftime('%H:%M:%S')}] {msg}")


# ============================================================================
# 接收方
# ============================================================================
class ReceiveWorker(QThread):
    """接收文件的线程"""
    progress = pyqtSignal(int, int, str, int, int, float)
    connection_received = pyqtSignal(str)
    finished_ok = pyqtSignal(int, list)
    error = pyqtSignal(str)

    def __init__(self, conn, addr):
        super().__init__()
        self.conn = conn
        self.addr = addr
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _cancelled_cb(self):
        return self._cancelled

    def run(self):
        try:
            self.connection_received.emit(self.addr[0])
            success, failed = receive_files(
                self.conn, self._save_dir,
                progress_cb=self.progress.emit,
                cancel_cb=self._cancelled_cb
            )
            self.finished_ok.emit(success, failed)
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))
            else:
                self.finished_ok.emit(0, ["已取消"])
        finally:
            try:
                self.conn.close()
            except Exception:
                pass


class ListenWorker(QThread):
    """监听连接的线程"""
    connection = pyqtSignal(object, tuple)
    error = pyqtSignal(str)
    listening = pyqtSignal()

    def __init__(self, port):
        super().__init__()
        self.port = port
        self._stopped = False
        self.server = None

    def stop(self):
        self._stopped = True
        if self.server:
            try:
                self.server.close()
            except Exception:
                pass

    def run(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind(("0.0.0.0", self.port))
            self.server.listen(5)
            self.server.settimeout(0.5)
            self.listening.emit()
            while not self._stopped:
                try:
                    conn, addr = self.server.accept()
                    if self._stopped:
                        conn.close()
                        break
                    self.connection.emit(conn, addr)
                except socket.timeout:
                    continue
                except OSError:
                    if self._stopped:
                        break
                    else:
                        raise
        except Exception as e:
            if not self._stopped:
                self.error.emit(str(e))
        finally:
            if self.server:
                try:
                    self.server.close()
                except Exception:
                    pass


class ReceiverWindow(QWidget):
    """接收方界面"""
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.listen_worker = None
        self.recv_workers = []
        self._save_dir = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 24)
        layout.setSpacing(16)

        # 顶部栏
        top_bar = QHBoxLayout()
        back_btn = QPushButton("← 返回")
        back_btn.setObjectName("btnSecondary")
        back_btn.setFixedWidth(96)
        back_btn.setFixedHeight(36)
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(back_btn)

        title = QLabel("接收文件")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignCenter)
        top_bar.addWidget(title, 1)

        top_bar.addSpacing(96)
        layout.addLayout(top_bar)

        # 本机 IP 提示
        ip_hint = QLabel(f"本机 IP：{get_local_ip()}  （请将此地址告诉传输方）")
        ip_hint.setObjectName("ipBadge")
        ip_hint.setAlignment(Qt.AlignCenter)
        ip_hint.setFixedHeight(34)
        layout.addWidget(ip_hint)

        # 监听设置卡片
        listen_card = QFrame()
        listen_card.setObjectName("card")
        add_card_shadow(listen_card)
        listen_layout = QVBoxLayout(listen_card)
        listen_layout.setContentsMargins(20, 18, 20, 18)
        listen_layout.setSpacing(12)

        listen_title = QLabel("监听设置")
        listen_title.setObjectName("cardTitle")
        listen_layout.addWidget(listen_title)

        listen_row = QHBoxLayout()
        port_label = QLabel("监听端口")
        port_label.setObjectName("fieldLabel")
        listen_row.addWidget(port_label)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(DEFAULT_PORT)
        listen_row.addWidget(self.port_spin, 1)

        dir_label = QLabel("保存到")
        dir_label.setObjectName("fieldLabel")
        listen_row.addWidget(dir_label)

        self.dir_edit = QLineEdit()
        self.dir_edit.setText(os.path.join(os.path.expanduser("~"), "Downloads", "接收文件"))
        listen_row.addWidget(self.dir_edit, 3)

        browse_btn = QPushButton("浏览")
        browse_btn.setObjectName("btnSecondary")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._choose_dir)
        listen_row.addWidget(browse_btn)

        listen_layout.addLayout(listen_row)
        layout.addWidget(listen_card)

        # 状态卡片
        status_card = QFrame()
        status_card.setObjectName("card")
        add_card_shadow(status_card)
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(20, 18, 20, 18)
        status_layout.setSpacing(12)

        status_row = QHBoxLayout()
        self.status_label = QLabel("未监听")
        self.status_label.setObjectName("statusLabel")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        self.speed_label = QLabel("")
        self.speed_label.setObjectName("speedLabel")
        status_row.addWidget(self.speed_label)
        status_layout.addLayout(status_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        status_layout.addWidget(self.progress_bar)

        layout.addWidget(status_card)

        # 开始/停止按钮
        self.listen_btn = QPushButton("开始监听")
        self.listen_btn.setObjectName("btnPrimary")
        self.listen_btn.setFixedHeight(48)
        self.listen_btn.setCursor(Qt.PointingHandCursor)
        self.listen_btn.clicked.connect(self._toggle_listen)
        layout.addWidget(self.listen_btn)

        # 日志
        log_label = QLabel("接收日志")
        log_label.setObjectName("fieldLabel")
        layout.addWidget(log_label)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(110)
        layout.addWidget(self.log_view)

    def _choose_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if folder:
            self.dir_edit.setText(folder)

    def _toggle_listen(self):
        if self.listen_worker and self.listen_worker.isRunning():
            self._stop_listen()
        else:
            self._start_listen()

    def _start_listen(self):
        port = self.port_spin.value()
        save_dir = self.dir_edit.text().strip()
        if not save_dir:
            QMessageBox.warning(self, "提示", "请选择保存目录")
            return
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir)
            except Exception as e:
                QMessageBox.warning(self, "提示", f"无法创建保存目录：{e}")
                return

        self._save_dir = save_dir

        self.listen_worker = ListenWorker(port)
        self.listen_worker.listening.connect(self._on_listening)
        self.listen_worker.connection.connect(self._on_connection)
        self.listen_worker.error.connect(self._on_listen_error)
        self.listen_worker.start()

        self.listen_btn.setText("正在监听...")
        self.port_spin.setEnabled(False)
        self.dir_edit.setEnabled(False)
        self._log(f"正在监听端口 {port}，等待传输方连接...")

    def _stop_listen(self):
        if self.listen_worker:
            self.listen_worker.stop()
        self.listen_btn.setText("开始监听")
        self.port_spin.setEnabled(True)
        self.dir_edit.setEnabled(True)
        self.status_label.setText("已停止监听")
        self._log("已停止监听")

    def _on_listening(self):
        self.listen_btn.setText("停止监听")
        self.status_label.setText("监听中，等待接收...")
        self._log("监听已启动")

    def _on_connection(self, conn, addr):
        worker = ReceiveWorker(conn, addr)
        worker._save_dir = self._save_dir
        worker.progress.connect(self._on_progress)
        worker.connection_received.connect(self._on_connection_received)
        worker.finished_ok.connect(lambda s, f, w=worker: self._on_finished(w, s, f))
        worker.error.connect(lambda m, w=worker: self._on_error(w, m))
        self.recv_workers.append(worker)
        worker.start()
        self._log(f"收到来自 {addr[0]} 的连接")

    def _on_connection_received(self, ip):
        self.status_label.setText(f"正在接收来自 {ip} 的文件...")
        self.speed_label.setText("")
        self.progress_bar.setValue(0)

    def _on_progress(self, cur, count, name, cur_size, total_size, speed):
        pct = int(cur_size / total_size * 100) if total_size > 0 else 0
        self.progress_bar.setValue(pct)
        self.progress_bar.setFormat(f"{pct}%  ({cur}/{count})")
        self.status_label.setText(f"正在接收：{name}")
        self.speed_label.setText(
            f"{format_size(cur_size)} / {format_size(total_size)}  ·  {format_speed(speed)}"
        )

    def _on_finished(self, worker, success, failed):
        if worker in self.recv_workers:
            self.recv_workers.remove(worker)
        self.progress_bar.setFormat("完成")
        self.status_label.setText(
            f"接收完成：成功 {success} 个，失败 {len(failed)} 个"
            if not self.listen_worker or not self.listen_worker.isRunning()
            else "接收完成，继续监听中..."
        )
        self.speed_label.setText("")
        for f in failed:
            self._log(f"[失败] {f}")
        self._log(f"接收完成：成功 {success} 个，失败 {len(failed)} 个")

    def _on_error(self, worker, msg):
        if worker in self.recv_workers:
            self.recv_workers.remove(worker)
        self.status_label.setText("接收出错")
        self.speed_label.setText("")
        self._log(f"[错误] {msg}")

    def _on_listen_error(self, msg):
        self.listen_btn.setText("开始监听")
        self.port_spin.setEnabled(True)
        self.dir_edit.setEnabled(True)
        self.status_label.setText("监听失败")
        self._log(f"[错误] {msg}")
        QMessageBox.critical(self, "监听失败", f"无法启动监听：\n{msg}")
        self.listen_worker = None

    def _log(self, msg):
        self.log_view.append(f"[{time.strftime('%H:%M:%S')}] {msg}")


# ============================================================================
# 主窗口
# ============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("局域网文件极速传输器")
        self.resize(760, 720)
        self.setMinimumSize(680, 640)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.role_page = self._build_role_page()
        self.sender_page = SenderWindow()
        self.receiver_page = ReceiverWindow()

        self.stack.addWidget(self.role_page)
        self.stack.addWidget(self.sender_page)
        self.stack.addWidget(self.receiver_page)

        self.sender_page.back_requested.connect(lambda: self.stack.setCurrentWidget(self.role_page))
        self.receiver_page.back_requested.connect(lambda: self.stack.setCurrentWidget(self.role_page))

    def _build_role_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 44, 40, 36)
        layout.setSpacing(20)

        title = QLabel("局域网文件极速传输器")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("无需网络，局域网内高速互传文件")
        subtitle.setObjectName("appSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        ip_badge = QLabel(f"本机 IP：{get_local_ip()}    默认端口：{DEFAULT_PORT}")
        ip_badge.setObjectName("ipBadge")
        ip_badge.setAlignment(Qt.AlignCenter)
        ip_badge.setFixedHeight(34)
        layout.addWidget(ip_badge)

        layout.addSpacing(18)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(28)

        send_card = self._make_role_card(
            "发送", "传输方", "发送文件",
            "选择文件并发送到\n局域网内的接收方",
            "#2f80ed", "#eaf2fd",
            lambda: self.stack.setCurrentWidget(self.sender_page)
        )
        cards_row.addWidget(send_card)

        recv_card = self._make_role_card(
            "接收", "接收方", "接收文件",
            "监听端口，接收传输方\n发送过来的文件",
            "#27ae60", "#e8f7ee",
            lambda: self.stack.setCurrentWidget(self.receiver_page)
        )
        cards_row.addWidget(recv_card)

        layout.addLayout(cards_row)

        layout.addStretch()

        tip = QLabel("使用说明：接收方先点击「开始监听」，传输方输入接收方 IP 后发送文件")
        tip.setObjectName("fieldLabel")
        tip.setAlignment(Qt.AlignCenter)
        layout.addWidget(tip)

        return page

    def _make_role_card(self, icon, title, action, desc, accent, badge_bg, onclick):
        card = QFrame()
        card.setObjectName("card")
        card.setCursor(Qt.PointingHandCursor)
        card.setMinimumHeight(300)
        card.setAttribute(Qt.WA_Hover, True)
        add_card_shadow(card, blur=30, y_offset=6, alpha=30)

        v = QVBoxLayout(card)
        v.setContentsMargins(28, 30, 28, 26)
        v.setSpacing(12)

        badge = QLabel(icon)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(84, 84)
        badge.setStyleSheet(
            f"background-color: {badge_bg}; color: {accent}; border-radius: 42px;"
            f"font-size: 24px; font-weight: bold;"
        )
        badge_wrap = QHBoxLayout()
        badge_wrap.addStretch()
        badge_wrap.addWidget(badge)
        badge_wrap.addStretch()
        v.addLayout(badge_wrap)

        v.addSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        title_label.setAlignment(Qt.AlignCenter)
        v.addWidget(title_label)

        desc_label = QLabel(desc)
        desc_label.setObjectName("cardDesc")
        desc_label.setAlignment(Qt.AlignCenter)
        v.addWidget(desc_label)

        v.addStretch()

        btn = QPushButton(action)
        btn.setFixedHeight(44)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(onclick)
        hover = "#2a72d4" if accent == "#2f80ed" else "#219653"
        pressed = "#2563b8" if accent == "#2f80ed" else "#1e8a4c"
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {accent}; color: white; border: none;"
            f"border-radius: 8px; padding: 11px 24px; font-size: 15px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: {hover}; }}"
            f"QPushButton:pressed {{ background-color: {pressed}; }}"
        )
        v.addWidget(btn)

        card.mousePressEvent = lambda e: onclick()

        return card


# ============================================================================
# 入口
# ============================================================================
def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    icon_path = resource_path("icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.setWindowIcon(QIcon(icon_path) if os.path.exists(icon_path) else QIcon())
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
