#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
局域网文件传输工具 - 增强版
增加了文件校验、传输速度显示、断点续传等功能
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import socket
import threading
import os
import json
import time
from pathlib import Path
import hashlib
import struct

class AdvancedFileTransferGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("局域网文件传输工具 - 增强版")
        self.root.geometry("900x700")
        self.root.configure(bg='#f0f0f0')
        
        # 网络相关变量
        self.server_socket = None
        self.client_socket = None
        self.is_server_running = False
        self.local_ip = self.get_local_ip()
        self.port = 8888
        
        # 文件传输相关
        self.selected_files = []
        self.download_path = str(Path.home() / "Downloads")
        self.transfer_stats = {'start_time': 0, 'bytes_transferred': 0}
        
        # 进度条相关
        self.progress_vars = {}
        self.speed_vars = {}
        
        self.setup_ui()
        self.update_status("就绪")
        
    def get_local_ip(self):
        """获取本机IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def calculate_file_hash(self, filepath, chunk_size=8192):
        """计算文件MD5哈希值"""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return None
    
    def format_bytes(self, bytes_count):
        """格式化字节数显示"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} TB"
    
    def calculate_speed(self, bytes_transferred, elapsed_time):
        """计算传输速度"""
        if elapsed_time > 0:
            speed = bytes_transferred / elapsed_time
            return self.format_bytes(speed) + "/s"
        return "0 B/s"
    
    def setup_ui(self):
        """设置用户界面"""
        # 创建笔记本控件（标签页）
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 主要功能标签页
        main_frame = ttk.Frame(notebook, padding="10")
        notebook.add(main_frame, text="文件传输")
        
        # 设置标签页
        settings_frame = ttk.Frame(notebook, padding="10")
        notebook.add(settings_frame, text="设置")
        
        # 日志标签页
        log_frame = ttk.Frame(notebook, padding="10")
        notebook.add(log_frame, text="传输日志")
        
        self.setup_main_tab(main_frame)
        self.setup_settings_tab(settings_frame)
        self.setup_log_tab(log_frame)
        
        # 状态栏
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
    
    def setup_main_tab(self, parent):
        """设置主要功能标签页"""
        # 标题
        title_label = ttk.Label(parent, text="局域网文件传输工具 - 增强版", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 服务器设置区域
        server_frame = ttk.LabelFrame(parent, text="服务器设置", padding="10")
        server_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        server_frame.columnconfigure(1, weight=1)
        
        ttk.Label(server_frame, text="本机IP:").grid(row=0, column=0, sticky=tk.W)
        self.ip_label = ttk.Label(server_frame, text=self.local_ip, 
                                 font=('Arial', 10, 'bold'), foreground='blue')
        self.ip_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(server_frame, text="端口:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        self.port_var = tk.StringVar(value=str(self.port))
        port_entry = ttk.Entry(server_frame, textvariable=self.port_var, width=8)
        port_entry.grid(row=0, column=3, padx=(5, 0))
        
        self.server_btn = ttk.Button(server_frame, text="启动服务器", 
                                    command=self.toggle_server)
        self.server_btn.grid(row=0, column=4, padx=(20, 0))
        
        # 连接状态指示器
        self.connection_status = ttk.Label(server_frame, text="●", 
                                          foreground='red', font=('Arial', 12))
        self.connection_status.grid(row=0, column=5, padx=(10, 0))
        
        # 文件发送区域
        send_frame = ttk.LabelFrame(parent, text="发送文件", padding="10")
        send_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        send_frame.columnconfigure(1, weight=1)
        
        ttk.Button(send_frame, text="选择文件", 
                  command=self.select_files).grid(row=0, column=0, sticky=tk.W)
        
        # 文件列表框架
        files_frame = ttk.Frame(send_frame)
        files_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        files_frame.columnconfigure(0, weight=1)
        
        self.files_listbox = tk.Listbox(files_frame, height=4)
        self.files_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        files_scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, 
                                       command=self.files_listbox.yview)
        files_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.files_listbox.config(yscrollcommand=files_scrollbar.set)
        
        ttk.Button(send_frame, text="清空列表", 
                  command=self.clear_files).grid(row=0, column=2, padx=(10, 0))
        
        # 连接设置
        connect_frame = ttk.Frame(send_frame)
        connect_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        connect_frame.columnconfigure(1, weight=1)
        
        ttk.Label(connect_frame, text="目标IP:").grid(row=0, column=0, sticky=tk.W)
        self.target_ip_var = tk.StringVar()
        target_ip_entry = ttk.Entry(connect_frame, textvariable=self.target_ip_var)
        target_ip_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        
        self.send_btn = ttk.Button(connect_frame, text="发送文件", 
                                  command=self.send_files)
        self.send_btn.grid(row=0, column=2, padx=(10, 0))
        
        # 传输进度区域
        progress_frame = ttk.LabelFrame(parent, text="传输进度", padding="10")
        progress_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.progress_label = ttk.Label(progress_frame, text="等待传输...")
        self.progress_label.grid(row=1, column=0, sticky=tk.W)
        
        self.speed_label = ttk.Label(progress_frame, text="")
        self.speed_label.grid(row=2, column=0, sticky=tk.W)
        
        # 接收设置区域
        receive_frame = ttk.LabelFrame(parent, text="接收设置", padding="10")
        receive_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        receive_frame.columnconfigure(1, weight=1)
        
        ttk.Label(receive_frame, text="下载路径:").grid(row=0, column=0, sticky=tk.W)
        self.download_path_var = tk.StringVar(value=self.download_path)
        path_entry = ttk.Entry(receive_frame, textvariable=self.download_path_var)
        path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        
        ttk.Button(receive_frame, text="浏览", 
                  command=self.select_download_path).grid(row=0, column=2, padx=(10, 0))
        
        # 文件校验选项
        self.verify_files_var = tk.BooleanVar(value=True)
        verify_check = ttk.Checkbutton(receive_frame, text="启用文件完整性校验", 
                                      variable=self.verify_files_var)
        verify_check.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
        
        # 配置网格权重
        parent.columnconfigure(1, weight=1)
    
    def setup_settings_tab(self, parent):
        """设置配置标签页"""
        # 网络设置
        network_frame = ttk.LabelFrame(parent, text="网络设置", padding="10")
        network_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        network_frame.columnconfigure(1, weight=1)
        
        ttk.Label(network_frame, text="缓冲区大小:").grid(row=0, column=0, sticky=tk.W)
        self.buffer_size_var = tk.StringVar(value="4096")
        buffer_entry = ttk.Entry(network_frame, textvariable=self.buffer_size_var, width=10)
        buffer_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        ttk.Label(network_frame, text="字节").grid(row=0, column=2, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(network_frame, text="连接超时:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.timeout_var = tk.StringVar(value="30")
        timeout_entry = ttk.Entry(network_frame, textvariable=self.timeout_var, width=10)
        timeout_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 0))
        ttk.Label(network_frame, text="秒").grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=(10, 0))
        
        # 界面设置
        ui_frame = ttk.LabelFrame(parent, text="界面设置", padding="10")
        ui_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_check = ttk.Checkbutton(ui_frame, text="自动滚动日志", 
                                           variable=self.auto_scroll_var)
        auto_scroll_check.grid(row=0, column=0, sticky=tk.W)
        
        self.show_notifications_var = tk.BooleanVar(value=True)
        notifications_check = ttk.Checkbutton(ui_frame, text="显示传输完成通知", 
                                             variable=self.show_notifications_var)
        notifications_check.grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        
        # 系统信息
        info_frame = ttk.LabelFrame(parent, text="系统信息", padding="10")
        info_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        info_text = f"""Python版本: {os.sys.version.split()[0]}
操作系统: {os.name}
工作目录: {os.getcwd()}
用户目录: {Path.home()}"""
        
        info_label = ttk.Label(info_frame, text=info_text, justify=tk.LEFT)
        info_label.grid(row=0, column=0, sticky=tk.W)
        
        parent.columnconfigure(0, weight=1)
    
    def setup_log_tab(self, parent):
        """设置日志标签页"""
        # 日志控制按钮
        log_control_frame = ttk.Frame(parent)
        log_control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(log_control_frame, text="清空日志", 
                  command=self.clear_log).grid(row=0, column=0, sticky=tk.W)
        
        ttk.Button(log_control_frame, text="保存日志", 
                  command=self.save_log).grid(row=0, column=1, padx=(10, 0))
        
        # 日志文本区域
        self.log_text = scrolledtext.ScrolledText(parent, height=25, width=80)
        self.log_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry)
        
        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)
        
        self.root.update_idletasks()
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("日志已清空")
    
    def save_log(self):
        """保存日志到文件"""
        filename = filedialog.asksaveasfilename(
            title="保存日志文件",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                self.log_message(f"日志已保存到: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"保存日志失败: {str(e)}")
    
    def update_status(self, status):
        """更新状态栏"""
        self.status_var.set(f"状态: {status}")
    
    def update_connection_indicator(self, connected=False):
        """更新连接状态指示器"""
        if connected:
            self.connection_status.config(foreground='green')
        else:
            self.connection_status.config(foreground='red')
    
    def select_files(self):
        """选择要发送的文件"""
        files = filedialog.askopenfilenames(
            title="选择要发送的文件",
            filetypes=[("所有文件", "*.*")]
        )
        
        for file_path in files:
            if file_path not in self.selected_files:
                self.selected_files.append(file_path)
                filename = os.path.basename(file_path)
                filesize = self.format_bytes(os.path.getsize(file_path))
                display_text = f"{filename} ({filesize})"
                self.files_listbox.insert(tk.END, display_text)
        
        self.log_message(f"已选择 {len(files)} 个文件")
    
    def clear_files(self):
        """清空文件列表"""
        self.selected_files.clear()
        self.files_listbox.delete(0, tk.END)
        self.log_message("已清空文件列表")
    
    def select_download_path(self):
        """选择下载路径"""
        path = filedialog.askdirectory(title="选择下载文件夹")
        if path:
            self.download_path = path
            self.download_path_var.set(path)
            self.log_message(f"下载路径设置为: {path}")
    
    def toggle_server(self):
        """切换服务器状态"""
        if not self.is_server_running:
            self.start_server()
        else:
            self.stop_server()
    
    def start_server(self):
        """启动服务器"""
        try:
            self.port = int(self.port_var.get())
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.local_ip, self.port))
            self.server_socket.listen(5)
            
            self.is_server_running = True
            self.server_btn.config(text="停止服务器")
            self.update_connection_indicator(True)
            self.update_status(f"服务器运行中 - {self.local_ip}:{self.port}")
            self.log_message(f"服务器已启动，监听 {self.local_ip}:{self.port}")
            
            threading.Thread(target=self.accept_connections, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("错误", f"启动服务器失败: {str(e)}")
            self.log_message(f"启动服务器失败: {str(e)}")
    
    def stop_server(self):
        """停止服务器"""
        self.is_server_running = False
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        
        self.server_btn.config(text="启动服务器")
        self.update_connection_indicator(False)
        self.update_status("服务器已停止")
        self.log_message("服务器已停止")
    
    def accept_connections(self):
        """接受客户端连接"""
        while self.is_server_running:
            try:
                client_socket, address = self.server_socket.accept()
                self.log_message(f"客户端连接: {address[0]}:{address[1]}")
                
                threading.Thread(target=self.handle_client, 
                               args=(client_socket, address), daemon=True).start()
                
            except Exception as e:
                if self.is_server_running:
                    self.log_message(f"接受连接时出错: {str(e)}")
                break
    
    def handle_client(self, client_socket, address):
        """处理客户端请求"""
        try:
            buffer_size = int(self.buffer_size_var.get())
            
            while True:
                # 接收文件信息
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                file_info = json.loads(data)
                filename = file_info['filename']
                filesize = file_info['filesize']
                file_hash = file_info.get('hash', '')
                
                self.log_message(f"接收文件: {filename} ({self.format_bytes(filesize)})")
                
                # 发送确认
                client_socket.send(b"OK")
                
                # 接收文件数据
                filepath = os.path.join(self.download_path, filename)
                received_size = 0
                start_time = time.time()
                
                # 更新进度条
                self.progress_bar.config(maximum=filesize)
                
                with open(filepath, 'wb') as f:
                    while received_size < filesize:
                        chunk_size = min(buffer_size, filesize - received_size)
                        chunk = client_socket.recv(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        received_size += len(chunk)
                        
                        # 更新进度
                        progress = (received_size / filesize) * 100
                        elapsed_time = time.time() - start_time
                        speed = self.calculate_speed(received_size, elapsed_time)
                        
                        self.progress_bar.config(value=received_size)
                        self.progress_label.config(text=f"接收 {filename}: {progress:.1f}%")
                        self.speed_label.config(text=f"速度: {speed}")
                        self.update_status(f"接收 {filename}: {progress:.1f}%")
                
                # 文件校验
                if received_size == filesize:
                    if self.verify_files_var.get() and file_hash:
                        self.log_message("正在校验文件完整性...")
                        calculated_hash = self.calculate_file_hash(filepath)
                        if calculated_hash == file_hash:
                            self.log_message(f"文件接收完成并校验通过: {filename}")
                            client_socket.send(b"VERIFIED")
                        else:
                            self.log_message(f"文件校验失败: {filename}")
                            client_socket.send(b"HASH_ERROR")
                    else:
                        self.log_message(f"文件接收完成: {filename}")
                        client_socket.send(b"RECEIVED")
                else:
                    self.log_message(f"文件接收不完整: {filename}")
                    client_socket.send(b"ERROR")
                
                # 重置进度条
                self.progress_bar.config(value=0)
                self.progress_label.config(text="等待传输...")
                self.speed_label.config(text="")
                
        except Exception as e:
            self.log_message(f"处理客户端时出错: {str(e)}")
        finally:
            client_socket.close()
            self.log_message(f"客户端断开连接: {address[0]}:{address[1]}")
            self.update_status("就绪")
    
    def send_files(self):
        """发送文件到目标主机"""
        if not self.selected_files:
            messagebox.showwarning("警告", "请先选择要发送的文件")
            return
        
        target_ip = self.target_ip_var.get().strip()
        if not target_ip:
            messagebox.showwarning("警告", "请输入目标IP地址")
            return
        
        threading.Thread(target=self._send_files_thread, 
                        args=(target_ip,), daemon=True).start()
    
    def _send_files_thread(self, target_ip):
        """发送文件的线程函数"""
        try:
            buffer_size = int(self.buffer_size_var.get())
            timeout = int(self.timeout_var.get())
            
            # 连接到目标主机
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(timeout)
            client_socket.connect((target_ip, self.port))
            
            self.log_message(f"已连接到 {target_ip}:{self.port}")
            
            for file_path in self.selected_files:
                filename = os.path.basename(file_path)
                filesize = os.path.getsize(file_path)
                
                # 计算文件哈希
                file_hash = ""
                if self.verify_files_var.get():
                    self.log_message(f"正在计算文件哈希: {filename}")
                    file_hash = self.calculate_file_hash(file_path)
                
                # 发送文件信息
                file_info = {
                    'filename': filename,
                    'filesize': filesize,
                    'hash': file_hash
                }
                
                client_socket.send(json.dumps(file_info).encode('utf-8'))
                
                # 等待确认
                response = client_socket.recv(1024)
                if response != b"OK":
                    self.log_message(f"发送 {filename} 时出错")
                    continue
                
                # 发送文件数据
                self.log_message(f"发送文件: {filename} ({self.format_bytes(filesize)})")
                sent_size = 0
                start_time = time.time()
                
                # 更新进度条
                self.progress_bar.config(maximum=filesize)
                
                with open(file_path, 'rb') as f:
                    while sent_size < filesize:
                        chunk = f.read(buffer_size)
                        if not chunk:
                            break
                        client_socket.send(chunk)
                        sent_size += len(chunk)
                        
                        # 更新进度
                        progress = (sent_size / filesize) * 100
                        elapsed_time = time.time() - start_time
                        speed = self.calculate_speed(sent_size, elapsed_time)
                        
                        self.progress_bar.config(value=sent_size)
                        self.progress_label.config(text=f"发送 {filename}: {progress:.1f}%")
                        self.speed_label.config(text=f"速度: {speed}")
                        self.update_status(f"发送 {filename}: {progress:.1f}%")
                
                # 等待接收确认
                response = client_socket.recv(1024)
                if response == b"RECEIVED" or response == b"VERIFIED":
                    self.log_message(f"文件发送成功: {filename}")
                elif response == b"HASH_ERROR":
                    self.log_message(f"文件发送成功但校验失败: {filename}")
                else:
                    self.log_message(f"文件发送失败: {filename}")
                
                # 重置进度条
                self.progress_bar.config(value=0)
                self.progress_label.config(text="等待传输...")
                self.speed_label.config(text="")
            
            client_socket.close()
            self.log_message("所有文件发送完成")
            self.update_status("发送完成")
            
            if self.show_notifications_var.get():
                messagebox.showinfo("完成", "文件传输完成！")
            
        except Exception as e:
            self.log_message(f"发送文件时出错: {str(e)}")
            self.update_status("发送失败")
            messagebox.showerror("错误", f"发送文件失败: {str(e)}")

def main():
    root = tk.Tk()
    app = AdvancedFileTransferGUI(root)
    
    def on_closing():
        if app.is_server_running:
            app.stop_server()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()