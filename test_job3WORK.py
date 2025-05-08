#pip install ezdxf
#pip install serial
#pip install pyserial
#pip install PyQt5-tools
#pip install pyqt5

import sys
import ezdxf
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMessageBox
import math
import serial
import serial.tools.list_ports
import time
import os

from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QComboBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPen, QPainterPath, QColor
from PyQt5.QtWidgets import QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsPathItem
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QProgressBar, QGraphicsScene, QGraphicsView)
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QTextEdit, QPushButton, QVBoxLayout, QWidget
from datetime import datetime
from PyQt5.QtGui import QTransform
from collections import defaultdict
from PyQt5.QtGui import QTransform
from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QBrush
from collections import defaultdict
from PyQt5.QtSerialPort import QSerialPort
from PyQt5.QtCore import QIODevice






class SettingsDialog(QDialog):
    config_updated = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки резки")
        self.setFixedWidth(300)
        layout = QFormLayout()


        self.curve_step_input = QLineEdit("1.0")
        self.steps_per_meter_x_input = QLineEdit("1000")
        self.steps_per_meter_y_input = QLineEdit("1000")
        self.speed_input = QLineEdit("500")
        self.invert_x_box = QComboBox()
        self.invert_x_box.addItems(["Нет", "Да"])
        self.invert_y_box = QComboBox()
        self.invert_y_box.addItems(["Нет", "Да"])
        self.com_port_box = QComboBox()
        self.refresh_ports()
        self.motion_program = []
        self.motion_index = 0
        self.total_distance = 0
        self.traveled_distance = 0
        self.start_time = None
        self.speed = 500  # по умолчанию (мм/с)
        self.baudrate_box = QComboBox()
        self.baudrate_box.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.node_tolerance_input = QLineEdit("0.5")
        self.delay_time_input = QLineEdit("500")  # значение по умолчанию 500 мс
        self.delay_angle_threshold_input = QLineEdit("170")  # новое поле, порог угла
        self.show_delay_markers_box = QComboBox()
        self.show_delay_markers_box.addItems(["Нет", "Да"])


        self.connect_button = QPushButton("Подключиться")
        self.save_button = QPushButton("Сохранить")
        
        layout.addRow("Шаги на метр (X):", self.steps_per_meter_x_input)
        layout.addRow("Шаги на метр (Y):", self.steps_per_meter_y_input)
        layout.addRow("Максимальная скорость (шаг/сек):", self.speed_input)
        layout.addRow("Инверсия X:", self.invert_x_box)
        layout.addRow("Инверсия Y:", self.invert_y_box)
        layout.addRow("COM порт:", self.com_port_box)
        layout.addRow("Скорость порта:", self.baudrate_box)
        layout.addRow("Допуск узлов (мм):", self.node_tolerance_input)
        layout.addRow("Шаг по дугам и кривым (мм):", self.curve_step_input)
        layout.addRow("Время DELAY (мс):", self.delay_time_input)
        layout.addRow("Показывать маркеры углов:", self.show_delay_markers_box)
        layout.addRow("Порог угла для DELAY (°):", self.delay_angle_threshold_input)

        layout.addRow(self.connect_button)
        layout.addRow(self.save_button)

        self.setLayout(layout)

        self.serial_connection = None
        self.connect_button.clicked.connect(self.try_connect)
        self.save_button.clicked.connect(self.save_settings)
        self.load_settings()

        

    def save_settings(self):
        settings = {
            'steps_per_meter_x': self.steps_per_meter_x_input.text(),
            'steps_per_meter_y': self.steps_per_meter_y_input.text(),
            'speed': self.speed_input.text(),
            'invert_x': self.invert_x_box.currentIndex(),
            'invert_y': self.invert_y_box.currentIndex(),
            'com_port': self.com_port_box.currentText(),
            'baudrate': self.baudrate_box.currentText(),
            'node_tolerance': self.node_tolerance_input.text(),
            'curve_step': self.curve_step_input.text(),
            'show_delay_markers': self.show_delay_markers_box.currentIndex(),
            'delay_time': self.delay_time_input.text(),
            'delay_angle_threshold': self.delay_angle_threshold_input.text(),


        }

        try:
            with open('settings.txt', 'w') as file:
                for key, value in settings.items():
                    file.write(f"{key}={value}\n")

            QMessageBox.information(self, "Успех", "Настройки сохранены.")

            # ⬇️ Отправим конфигурацию напрямую, если подключено
            parent = self.parent()
            if (
                parent and hasattr(parent, "serial") and parent.serial
                and hasattr(parent, "already_ready") and parent.already_ready
            ):
                parent.log_window.append_log("⚙️ Настройки сохранены — отправка конфигурации в Arduino...")
                parent.send_config_sequentially()
            else:
                print("ℹ️ Настройки сохранены, но Arduino не подключена или не готова.")

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки: {e}")


    def load_settings(self):
        if not os.path.exists('settings.txt'):
            return  

        try:
            with open('settings.txt', 'r') as file:
                settings = {}
                for line in file.readlines():
                    key, value = line.strip().split('=')
                    settings[key] = value

            self.steps_per_meter_x_input.setText(settings.get('steps_per_meter_x', '1000'))
            self.steps_per_meter_y_input.setText(settings.get('steps_per_meter_y', '1000'))
            self.speed_input.setText(settings.get('speed', '500'))
            self.invert_x_box.setCurrentIndex(int(settings.get('invert_x', 0)))
            self.invert_y_box.setCurrentIndex(int(settings.get('invert_y', 0)))
            self.com_port_box.setCurrentText(settings.get('com_port', ''))
            self.baudrate_box.setCurrentText(settings.get('baudrate', '9600'))
            self.node_tolerance_input.setText(settings.get('node_tolerance', '0.5'))
            self.curve_step_input.setText(settings.get('curve_step', '1.0'))
            self.show_delay_markers_box.setCurrentIndex(int(settings.get('show_delay_markers', 1)))
            self.delay_time_input.setText(settings.get('delay_time', '500'))
            self.delay_angle_threshold_input.setText(settings.get('delay_angle_threshold', '170'))




        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить настройки: {e}")

    def refresh_ports(self):
        self.com_port_box.clear()
        ports = serial.tools.list_ports.comports()
        self.com_port_box.addItems([port.device for port in ports])

    def try_connect(self):
        port = self.com_port_box.currentText()
        baud = int(self.baudrate_box.currentText())
        try:
            self.serial_connection = serial.Serial(port, baudrate=baud, timeout=1)
            QMessageBox.information(self, "Успех", f"Подключено к {port}")
        except Exception as e:
            self.serial_connection = None
            QMessageBox.critical(self, "Ошибка", str(e))

    def get_node_tolerance(self):
        try:
            return float(self.node_tolerance_input.text())
        except ValueError:
            return 0.5

    def get_serial_connection(self):
        return self.serial_connection

    def try_connect(self):
        port = self.com_port_box.currentText()
        baud = int(self.baudrate_box.currentText())
        try:
            self.serial_connection = serial.Serial(port, baudrate=baud, timeout=1)
            QMessageBox.information(self, "Успех", f"Подключено к {port}")
            self.accept()  # автоматически закрываем настройки с применением
        except Exception as e:
            self.serial_connection = None
            QMessageBox.critical(self, "Ошибка", str(e))



class LogWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Лог общения с Arduino")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        self.setLayout(layout)

    def append_log(self, message):
        timestamp = datetime.now().strftime("[%H:%M:%S.%f]")[:-2] 
        self.log_text.append(f"{timestamp} {message}")





class MainWindow(QMainWindow):


    def update_position_marker(self, x, y):
        new_pos = QPointF(x, y)

        # Начало пути — всегда от (0, 0)
        if not hasattr(self, "trace_path") or self.trace_path is None:
            self.trace_path = QPainterPath()
            self.trace_path.moveTo(QPointF(0, 0))  # ← начинаем всегда с (0, 0)

        self.trace_path.lineTo(new_pos)

        # Удалить старый путь
        if self.trace_path_item:
            self.scene.removeItem(self.trace_path_item)

        self.trace_path_item = self.scene.addPath(self.trace_path, self.path_pen)

        # Удалить старый указатель
        if self.position_marker:
            self.scene.removeItem(self.position_marker)

        self.position_marker = QGraphicsEllipseItem(
            x - self.marker_radius, y - self.marker_radius,
            2 * self.marker_radius, 2 * self.marker_radius
        )
        self.position_marker.setBrush(self.marker_brush)
        self.position_marker.setPen(QPen(Qt.NoPen))
        self.scene.addItem(self.position_marker)

        self.current_position = new_pos



    def read_status_response(self):
        try:
            buffer = []
            timeout = 1.5
            start_time = time.time()

            while time.time() - start_time < timeout:
                while self.serial.canReadLine():
                    line = bytes(self.serial.readLine()).decode(errors="ignore").strip()

                    if line:
                        buffer.append(line)
                time.sleep(0.05)

            if buffer:
                self.device_status_label.append("\n".join(buffer))
            else:
                self.device_status_label.append("Контроллер не ответил.")
        except Exception as e:
            self.device_status_label.append(f"Ошибка чтения: {e}")







    def send_manual_status_request(self):
        if self.serial and self.serial.isOpen():
            try:
                self.serial.write(b'STATUS\n')
                QTimer.singleShot(200, self.read_status_response)
            except Exception as e:
                self.device_status_label.append(f"Ошибка отправки: {e}")
        else:
            self.device_status_label.append("Нет подключения к контроллеру.")




    def send_config_sequentially(self):
        settings_path = "settings.txt"
        if not os.path.exists(settings_path):
            print("⚠ Файл настроек не найден.")
            return

        try:
            with open(settings_path, 'r') as f:
                settings = {}
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        settings[key] = value

            speed = settings.get("speed", "500")
            steps_x = settings.get("steps_per_meter_x", "1000")
            steps_y = settings.get("steps_per_meter_y", "1000")
            invert_x = settings.get("invert_x", "0")
            invert_y = settings.get("invert_y", "0")

            self.config_steps = [
                ("CONFIG_SPEED", f"{speed}", "SPEED SET"),
                ("CONFIG_STEPS", f"{steps_x} {steps_y}", "STEPS SET"),
                ("CONFIG_INVERT", f"{invert_x} {invert_y}", "INVERT SET"),
            ]



            self.config_finished = False
            self.waiting_for_config_response = None

            self._send_next_config()

        except Exception as e:
            print(f"❌ Ошибка чтения настроек: {e}")


    def _send_next_config(self):
        if not self.config_steps:
            print("✅ Конфигурация завершена.")
            self.config_finished = True
            self.waiting_for_config_response = None
            return

        cmd_name, cmd_args, expected_response = self.config_steps.pop(0)
        full_cmd = f"{cmd_name} {cmd_args}\n"

        print(f"➡ Отправка: {full_cmd.strip()} (ждём: {expected_response})")
        self.serial.write(full_cmd.encode())
        self.log_window.append_log(f"> {full_cmd.strip()}")

        self.waiting_for_config_response = expected_response


    




    def load_settings_at_startup(self):
        settings_path = "settings.txt"
        if not os.path.exists(settings_path):
            return

        try:
            with open(settings_path, 'r') as f:
                settings = {}
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        settings[key] = value

            self.steps_per_meter_x = int(settings.get('steps_per_meter_x', '1000'))
            self.steps_per_meter_y = int(settings.get('steps_per_meter_y', '1000'))
            self.speed = int(settings.get('speed', '500'))
            self.invert_x = int(settings.get('invert_x', 0))
            self.invert_y = int(settings.get('invert_y', 0))
            self.node_tolerance = float(settings.get('node_tolerance', 0.5))
            self.curve_step = float(settings.get('curve_step', 1.0))
            self.delay_time = int(settings.get('delay_time', 500))
            self.show_delay_markers = int(settings.get('show_delay_markers', 1)) == 1
            self.delay_angle_threshold = int(settings.get('delay_angle_threshold', 170))

        except Exception as e:
            print(f"⚠ Ошибка чтения настроек при старте: {e}")


    def try_auto_connect(self):
        settings_path = "settings.txt"
        if not os.path.exists(settings_path):
            print("⚠ Файл настроек не найден, авто-подключение невозможно.")
            return

        try:
            settings = {}
            with open(settings_path, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        settings[key] = value

            port = settings.get("com_port", "")
            baudrate = int(settings.get("baudrate", "9600"))

            if not port:
                print("⚠ COM порт не указан в настройках.")
                return

            self.serial = QSerialPort()
            self.serial.setPortName(port)
            self.serial.setBaudRate(baudrate)
            if self.serial.open(QIODevice.ReadWrite):
                self.log_window.append_log(f"✅ Подключено к {port} на скорости {baudrate}")
                QTimer.singleShot(1500, self.setup_arduino_connection)
            else:
                self.status_label.setText("Ошибка открытия порта!")


            self.status_label.setText("Статус: Ожидание\nArduino: Подключено")


        except Exception as e:
            print(f"❌ Авто-подключение не удалось: {e}")
            self.serial = None

    def setup_arduino_connection(self):
        self.serial.readyRead.connect(self.handle_arduino_response)
        self.status_label.setText("Статус: Ожидание\nArduino: Подключено")






    
    def closeEvent(self, event):
        if self.status_thread:
            self.status_thread.running = False
            self.status_thread.quit()
            self.status_thread.wait()
        event.accept()

    
    def log_status(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        current_text = self.system_status_log.toPlainText()
        new_text = f"{current_text}\n{full_message}" if current_text else message
        self.system_status_log.setPlainText(new_text)
        self.system_status_log.verticalScrollBar().setValue(
            self.system_status_log.verticalScrollBar().maximum()
        )
  
    def confirm_exit(self):
        reply = QMessageBox.question(
            self,
            "Выход",
            "Вы действительно хотите выйти из программы?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.close()

    def show_log_window(self):
        self.log_window.show()

    def stop_clicked(self):
        if not self.in_progress:
            return

        self.in_progress = False
        self.paused = False
        self.motion_index = 0
        self.motion_program = []
        self.traveled_distance = 0
        self.total_distance = 0
        self.progress_bar.setValue(0)
        self.progress_label.setText("Остановлено")
        self.pause_btn.setText("Пауза")

        if self.serial:
            self.serial.write(b'ABORT\n')
            self.log_window.append_log(">ABORT")

        self.status_label.setText("Резка остановлена.")

    
    def handle_arduino_response(self):
        try:
            while self.serial.canReadLine():
                response = bytes(self.serial.readLine()).decode(errors="ignore").strip()

                if not response:
                    continue

                print(f"⬅ Ответ от Arduino: {response}")
                self.log_window.append_log(f"< {response}")

                if self.waiting_for_config_response:
                    if response.upper() == self.waiting_for_config_response.upper():
                        print(f"✅ Получен ожидаемый ответ {response}")
                        self.waiting_for_config_response = None
                        self._send_next_config()
                    else:
                        print(f"⚠ Игнорируем ответ {response} во время настройки")
                    return

                if response.upper() == "CUTTING STARTED":
                    self.send_next_batch()

                elif response.upper() == "NEED MORE":
                    self.send_next_batch()

             
                if response.upper().startswith("OKE"):
                    parts = response.split()
                    if len(parts) == 2 and parts[1].isdigit():
                        ack_index = int(parts[1])
                        if self.waiting_for_ack == ack_index:
                            self.waiting_for_ack = None
                            if self.pending_queue and self.pending_queue[0] == ack_index:
                                self.pending_queue.pop(0)
                            self.retry_timer.stop()

                            # 🟢 Если больше нечего отправлять и подтверждать — отправляем DONE
                            if not self.pending_queue and self.motion_index >= len(self.motion_program):
                                self.serial.write(b'DONE\n')
                                self.log_window.append_log("> Отправлено DONE")
                            else:
                                self.try_send_next()
                
                elif response.upper() == "DONE":
                    self.status_label.setText("Резка завершена.")
                    self.in_progress = False
                    self.cutting_mode = False

                elif response.upper() == "READY":
                    time.sleep(0.5)
                    self.send_config_sequentially()

        except Exception as e:
            self.status_label.setText(f"Ошибка связи: {e}")
            self.status_label.setWordWrap(True)  # активирует автоматический перенос строк




    def send_next_batch(self):
        if not self.serial or not self.in_progress:
            return
        # Формируем пакет команд (batch)
        
        batch = self.motion_program  # Сегмент команд для отправки
          # Обновляем указатель

        # Отправляем команду из batch
        for cmd in batch:
            index = int(cmd.split()[0])  # Получаем индекс из команды
            self.pending_commands[index] = cmd
            self.pending_queue.append(index)
        self.motion_index = len(self.motion_program)
        self.try_send_next()  # Отправляем первую команду из batch

        # Устанавливаем флаг ожидания подтверждения для этой команды
        self.waiting_for_ack = self.pending_queue[0]


       

    def try_send_next(self, delay=0.2):
        if self.waiting_for_ack is not None:
            return  # Ждём ACK

        if not self.pending_queue:
            return  # Больше нечего отправлять

        next_index = self.pending_queue[0]
        cmd = self.pending_commands[next_index]
        self.serial.write((cmd.strip() + '\n').encode())
        self.log_window.append_log(f"> {cmd.strip()}")

        self.waiting_for_ack = next_index

        # Запускаем таймер на 1 секунду для возможной повторной отправки
        self.retry_timer.start(3000)
        time.sleep(delay)  # Задержка после отправки каждой команды


    def retry_command(self):
        if self.waiting_for_ack is None:
            return  # Подтверждение уже пришло

        index = self.waiting_for_ack
        cmd = self.pending_commands.get(index)
        if cmd:
            self.serial.write((cmd.strip() + '\n').encode())
            self.log_window.append_log(f"> {cmd.strip()}")
            self.retry_timer.start(3000)  # Перезапускаем таймер ещё на 1 секунду
            

    def start_clicked(self):
        if not self.serial:
            QMessageBox.warning(self, "Нет подключения", "Подключитесь к Arduino")
            return

        if not self.motion_program:
            QMessageBox.warning(self, "Нет программы", "Сначала загрузите DXF и проверьте трассировку")
            return

        # Получаем значения из настроек
        try:
            speed = self.speed
            steps_per_meter_x = self.steps_per_meter_x
            steps_per_meter_y = self.steps_per_meter_y
            invert_x = self.invert_x
            invert_y = self.invert_y
        except ValueError:
            QMessageBox.warning(self, "Ошибка ввода", "Проверьте правильность введенных значений.")
            return

    

        # Отправляем команду START
        self.serial.clear(QSerialPort.Input)
        self.serial.write(b'START\n')
        self.log_window.append_log("> START")
    
        # Стартовые настройки и состояние
        self.status_label.setText("Ожидание разгона струны...")
        self.motion_index = 0
        self.paused = False
        self.in_progress = True
        self.pause_btn.setText("Пауза")
    
        # Таймер для продолжения выполнения
        
        self.start_time = time.time()

    def pause_resume_clicked(self):
        if not self.serial or not self.in_progress:
            return

        if not self.paused:
            self.paused = True
            self.serial.write(b'PAUSE\n')
            self.log_window.append_log("> PAUSE")
            self.status_label.setText("Пауза: выполнение приостановлено.")
            self.pause_btn.setText("Продолжить")
        else:
            self.paused = False
            self.serial.write(b'RESUME\n')
            self.log_window.append_log("> RESUME")
            self.status_label.setText("Возобновление... ждём разгон струны.")
            self.pause_btn.setText("Пауза")
            
    



    def check_trace(self, manual=False):
        
        tolerance = 0.1
        connections = defaultdict(int)
        segments = set()
        segments_dup = set()

        # Удаляем старые маркеры задержек
        old_markers = list(getattr(self, "delay_markers", []))
        self.delay_markers.clear()

        for marker in old_markers:
            if marker.scene() is not None:
                self.scene.removeItem(marker)


        def normalize_point(p):
            return (round(p[0], 3), round(p[1], 3))

        def segment_key(p1, p2):
            a, b = sorted([normalize_point(p1), normalize_point(p2)])
            return (a, b)

        if self.motion_program and self.motion_program[0].strip().endswith("0.00 0.00"):
            print("🧹 Удалена стартовая команда GOTO 0.00 0.00")
            self.motion_program.pop(0)

        for item in self.geometry_items:
            points = []

            if isinstance(item, QGraphicsLineItem):
                line = item.line()
                points = [(line.x1(), line.y1()), (line.x2(), line.y2())]

            elif isinstance(item, QGraphicsPathItem):
                path = item.path()
                for i in range(path.elementCount()):
                    e = path.elementAt(i)
                    points.append((e.x, e.y))

            elif isinstance(item, QGraphicsEllipseItem):
                rect = item.rect()
                cx = rect.center().x()
                cy = rect.center().y()
                r = rect.width() / 2
                points = [(cx + r, cy), (cx - r, cy)]

            if len(points) >= 2:
                for i in range(len(points) - 1):
                    p1 = normalize_point(points[i])
                    p2 = normalize_point(points[i + 1])
                    print(f"[SEGMENT] ({p1[0]:.2f}, {p1[1]:.2f}) -> ({p2[0]:.2f}, {p2[1]:.2f})")

                    connections[p1] += 1
                    connections[p2] += 1

                    key = segment_key(p1, p2)
                    if key in segments:
                        segments_dup.add(key)
                    else:
                        segments.add(key)
            elif len(points) == 1:
                p = normalize_point(points[0])
                connections[p] += 1

        # Обрывы
        one_connection_points = [pt for pt, count in connections.items() if count == 1]
        extra_broken_points = one_connection_points[2:] if len(one_connection_points) > 2 else []

        broken = len(extra_broken_points)
        duplicates = 0

        for i, (x, y) in enumerate(extra_broken_points):
            print(f"[!] Обрыв #{i+1} в точке: ({x:.2f}, {y:.2f})")

        broken_coords = "\n".join([f"({x:.2f}, {y:.2f})" for x, y in extra_broken_points])
        marker_radius = 3
        marker_pen = QPen(QColor("red"))
        marker_brush = QColor("red")
        for (x, y) in extra_broken_points:
            ellipse = QGraphicsEllipseItem(
                x - marker_radius, y - marker_radius,
                2 * marker_radius, 2 * marker_radius
            )
            ellipse.setPen(marker_pen)
            ellipse.setBrush(marker_brush)
            self.scene.addItem(ellipse)

        message = f"Обрывов: {broken}\nДубликатов: {duplicates}\nЛишние фигуры: 0"
        if broken_coords:
            message += f"\n\nКоординаты обрывов:\n{broken_coords}"

        allow_cutting = False

        if broken == 1 and manual:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Проверка трассировки")
            msg_box.setText(message)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.addButton("OK", QMessageBox.AcceptRole)
            allow_button = msg_box.addButton("Разрешить резку", QMessageBox.YesRole)

            msg_box.exec_()

            if msg_box.clickedButton() == allow_button:
                confirm = QMessageBox.question(
                    self,
                    "Подтверждение",
                    "Вы точно хотите запустить резку с ошибкой трассировки?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if confirm == QMessageBox.Yes:
                    allow_cutting = True

        else:
            QMessageBox.warning(self, "Проверка трассировки", message)



        if broken == 0 or allow_cutting:
            self.motion_program = []
            self.total_distance = 0
            self.traveled_distance = 0

            graph = defaultdict(list)
            for a, b in segments:
                graph[a].append(b)
                graph[b].append(a)

            def traverse_path(start, graph):
                visited_segments = set()
                path = [start]
                current = start

                while True:
                    neighbors = graph[current]
                    next_point = None

                    for neighbor in neighbors:
                        key = tuple(sorted([current, neighbor]))
                        if key not in visited_segments:
                            visited_segments.add(key)
                            next_point = neighbor
                            break

                    if next_point is None:
                        break

                    path.append(next_point)
                    current = next_point

                return path

            start_point = (0.0, 0.0)
            path_points = traverse_path(start_point, graph)

            
            self.motion_program = []
            seq_num = 0
            prev_pt = path_points[0]

            for idx in range(1, len(path_points)):
                curr_pt = path_points[idx]
                cmd = f"{seq_num} {curr_pt[0]:.2f} {curr_pt[1]:.2f}"
                self.motion_program.append(cmd)
                seq_num += 1
               

                # --- Здесь определяем необходимость вставки DELAY ---
                delay_needed = False

                # Найти тип сегмента между prev_pt -> curr_pt
                segment_type_prev = None
                for seg in self.segment_types:
                    if (self.is_close(prev_pt, seg['start']) and self.is_close(curr_pt, seg['end'])) or \
                       (self.is_close(prev_pt, seg['end']) and self.is_close(curr_pt, seg['start'])):
                        segment_type_prev = seg['type']
                        break

                # Найти тип следующего сегмента, если есть
                angle = None
                next_pt = None
                segment_type_next = None
                
                if idx + 1 < len(path_points):
                    next_pt = path_points[idx + 1]
                    segment_type_next = None
                    for seg in self.segment_types:
                        if (self.is_close(curr_pt, seg['start']) and self.is_close(next_pt, seg['end'])) or \
                           (self.is_close(curr_pt, seg['end']) and self.is_close(next_pt, seg['start'])):
                            segment_type_next = seg['type']
                            break
                    angle = self.calculate_angle(prev_pt, curr_pt, next_pt)


                # Проверка углов и типов
                if segment_type_prev and segment_type_next:

                    if segment_type_prev == "line" and segment_type_next == "curve":
                        if angle is not None and (10 < angle < self.delay_angle_threshold):
                            delay_needed = True
                    elif segment_type_prev == "curve" and segment_type_next == "line":
                        if angle is not None and (10 < angle < self.delay_angle_threshold):
                            delay_needed = True
                    elif segment_type_prev == "line" and segment_type_next == "line":
                        if angle is not None and angle < self.delay_angle_threshold:
                            delay_needed = True
                    elif segment_type_prev == "curve" and segment_type_next == "curve":
                        if angle is not None and angle < self.delay_angle_threshold:
                            delay_needed = True


                if delay_needed:
                    delay_cmd = f"{seq_num} {self.delay_time}"
                    self.motion_program.append(delay_cmd)
                    seq_num += 1


                    if getattr(self, "show_delay_markers", True):
                        marker_radius = 2
                        ellipse = QGraphicsEllipseItem(
                            curr_pt[0] - marker_radius, curr_pt[1] - marker_radius,
                            2 * marker_radius, 2 * marker_radius
                        )
                        purple = QColor(128, 0, 128)
                        pen = QPen(purple)
                        pen.setWidth(1)
                        ellipse.setPen(pen)
                        ellipse.setBrush(QBrush(purple))
                        self.scene.addItem(ellipse)
                        self.delay_markers.append(ellipse)


                prev_pt = curr_pt


                

            self.total_distance = 0
            for i in range(1, len(path_points)):
                a = path_points[i - 1]
                b = path_points[i]
                self.total_distance += math.hypot(b[0] - a[0], b[1] - a[1])

            print("📋 Сформированные команды:")
            for i, cmd in enumerate(self.motion_program):
                print(f"{i+1:03d}: {cmd.strip()}")

            self.progress_bar.setValue(0)
            self.progress_label.setText("0% - Осталось: расчёт...")
            self.status_label.setText(f"Готово к резке. Команд: {len(self.motion_program)}")


        else:
            QMessageBox.warning(self, "Проверка трассировки", message)
            self.motion_program = []
            self.status_label.setText("Обнаружены ошибки трассировки. Резка невозможна.")
            self.total_distance = 0


    def calculate_angle(self, p1, p2, p3):  #Вычислить угол в точке p2 между p1-p2-p3
        a = (p1[0] - p2[0], p1[1] - p2[1])
        b = (p3[0] - p2[0], p3[1] - p2[1])

        dot_product = a[0] * b[0] + a[1] * b[1]
        mag_a = math.hypot(a[0], a[1])
        mag_b = math.hypot(b[0], b[1])

        if mag_a == 0 or mag_b == 0:
            return 180

        cos_theta = dot_product / (mag_a * mag_b)
        cos_theta = max(min(cos_theta, 1), -1)  # защита от выхода за пределы acos
        angle_rad = math.acos(cos_theta)
        return math.degrees(angle_rad)


        
    def distance(self, p1, p2):
        return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

    def is_close(self, p1, p2, tol=0.01):
        return self.distance(p1, p2) < tol

    def __init__(self):
        super().__init__()

        # --- Основные переменные ---
        self.serial = None
        self.geometry_items = []
        self.segment_types = []  # здесь будем сохранять типы сегментов (line/curve)
        self.trace_points = []  # сюда сохраним точки чертежа
        self.motion_program = []
        self.motion_index = 0
        self.total_distance = 0
        self.traveled_distance = 0
        self.speed = 7054
        self.steps_per_meter_x = 7084
        self.steps_per_meter_y = 7084
        self.invert_x = 0
        self.invert_y = 0
        self.node_tolerance = 0.5
        self.curve_step = 1.0
        self.delay_time = 500  # значение по умолчанию 500 мс
        self.delay_angle_threshold = 170  # угол по умолчанию

        self.pending_commands = {}        # index: command_text
        self.pending_queue = []           # список индексов команд
        self.waiting_for_ack = None       # текущий индекс, для которого ждем ACK
        self.batch_pointer = 0

        self.retry_timer = QTimer()
        self.retry_timer.setSingleShot(True)
        self.retry_timer.timeout.connect(self.retry_command)



        self.trace_path_item = None
        self.position_marker = None
        self.current_position = QPointF(0, 0)
        self.path_pen = QPen(QColor("green"), 1)
        self.marker_brush = QBrush(QColor("red"))
        self.marker_radius = 3
        self.delay_markers = []

        self.waiting_for_config_response = None
        self.config_finished = True
        self.config_steps = []


        self.paused = False
        self.in_progress = False
        self.status_timer = None
        self.status_thread = None
        self.log_window = LogWindow(self)

        # --- Настройка окна ---
        self.setWindowTitle("Станок резки минеральной ваты")
        self.setGeometry(100, 100, 1200, 800)

        # --- UI ---
        self.init_ui()

        # --- Попытка автоматического подключения ---
        self.try_auto_connect()
        self.load_settings_at_startup()




    def load_dxf_file(self):
        scale_factor = 1 # если меняем - масштаб резки меняется (0.5 уменьшить в 2 раза координаты)

        settings_path = "settings.txt"
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r") as f:
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            if key == "curve_step":
                                self.curve_step = float(value)

            except Exception as e:
                print(f"⚠ Не удалось загрузить curve_step: {e}")

        
        file_path, _ = QFileDialog.getOpenFileName(self, "Открыть DXF файл", "", "DXF Files (*.dxf)")
        if not file_path:
            return

        self.file_label.setText(file_path.split("/")[-1])
        self.segment_types.clear()
        self.scene.clear()
        self.geometry_items.clear()

        try:
            doc = ezdxf.readfile(file_path)
            msp = doc.modelspace()
            pen = QPen(Qt.blue)
            pen.setWidthF(0.5)  # ⬅️ ЗАДАЛИ ТОЛЩИНУ ЛИНИЙ


            for e in msp:
                layer = e.dxf.layer
                if layer not in ['LAYER1', 'LAYER2']:
                    continue

                dxftype = e.dxftype()

                if dxftype == 'LINE':
                    start = e.dxf.start
                    end = e.dxf.end
                    item = QGraphicsLineItem(
                        start.x * scale_factor,
                        start.y * scale_factor,
                        end.x * scale_factor,
                        end.y * scale_factor
                    )
                    item.setPen(pen)
                    self.scene.addItem(item)
                    self.geometry_items.append(item)
                    self.segment_types.append({
                        'start': (round(start.x * scale_factor, 3), round(start.y * scale_factor, 3)),
                        'end': (round(end.x * scale_factor, 3), round(end.y * scale_factor, 3)),
                        'type': 'line'
                    })


                elif dxftype in ['LWPOLYLINE', 'POLYLINE']:
                    try:
                        path = QPainterPath()
                        first = True
                        for x, y in e.flattening(distance=self.curve_step):

                            x *= scale_factor
                            y *= scale_factor
                            if first:
                                path.moveTo(x, y)
                                first = False
                            else:
                                path.lineTo(x, y)
                        item = QGraphicsPathItem(path)
                        item.setPen(pen)
                        self.scene.addItem(item)
                        self.geometry_items.append(item)
                        # Добавляем все сегменты пути как кривые
                        for i in range(path.elementCount() - 1):
                            p1 = path.elementAt(i)
                            p2 = path.elementAt(i + 1)
                            self.segment_types.append({
                                'start': (round(p1.x, 3), round(p1.y, 3)),
                                'end': (round(p2.x, 3), round(p2.y, 3)),
                                'type': 'curve'
                            })

                    except Exception as ex:
                        print(f"[Ошибка POLYLINE] {ex}")

                elif dxftype == 'CIRCLE':
                    center = e.dxf.center
                    radius = e.dxf.radius
                    circle_length = 2 * math.pi * radius
                    segments = max(1, int(circle_length / self.curve_step))  # ⬅️ подставляем шаг из настроек
                    angle_step = 2 * math.pi / segments

                    path = QPainterPath()
                    for i in range(segments + 1):
                        angle = i * angle_step
                        x = (center.x + radius * math.cos(angle)) * scale_factor
                        y = (center.y + radius * math.sin(angle)) * scale_factor
                        if i == 0:
                            path.moveTo(x, y)
                        else:
                            path.lineTo(x, y)

                    item = QGraphicsPathItem(path)
                    item.setPen(pen)
                    self.scene.addItem(item)
                    self.geometry_items.append(item)
                    # Добавляем все сегменты пути как кривые
                    for i in range(path.elementCount() - 1):
                            p1 = path.elementAt(i)
                            p2 = path.elementAt(i + 1)
                            self.segment_types.append({
                                'start': (round(p1.x, 3), round(p1.y, 3)),
                                'end': (round(p2.x, 3), round(p2.y, 3)),
                                'type': 'curve'
                            })

                elif dxftype == 'ARC':
                    center = e.dxf.center
                    radius = e.dxf.radius
                    start_angle = e.dxf.start_angle
                    end_angle = e.dxf.end_angle

                    start_rad = math.radians(start_angle)
                    end_rad = math.radians(end_angle)
                    if end_rad < start_rad:
                        end_rad += 2 * math.pi

                    angle_rad = end_rad - start_rad
                    arc_length = radius * angle_rad
                    segments = max(1, int(arc_length / self.curve_step))  # ⬅️ подставляем шаг из настроек
                    angle_step = angle_rad / segments

                    path = QPainterPath()
                    for i in range(segments + 1):
                        angle = start_rad + i * angle_step
                        x = (center.x + radius * math.cos(angle)) * scale_factor
                        y = (center.y + radius * math.sin(angle)) * scale_factor
                        if i == 0:
                            path.moveTo(x, y)
                        else:
                            path.lineTo(x, y)

                    item = QGraphicsPathItem(path)
                    item.setPen(pen)
                    self.scene.addItem(item)
                    self.geometry_items.append(item)
                    # Добавляем все сегменты пути как кривые
                    for i in range(path.elementCount() - 1):
                            p1 = path.elementAt(i)
                            p2 = path.elementAt(i + 1)
                            self.segment_types.append({
                                'start': (round(p1.x, 3), round(p1.y, 3)),
                                'end': (round(p2.x, 3), round(p2.y, 3)),
                                'type': 'curve'
                            })


            # Сохраняем все точки из чертежа
            points_set = set()

            for item in self.geometry_items:
                if isinstance(item, QGraphicsLineItem):
                    line = item.line()
                    points_set.add((line.x1(), line.y1()))
                    points_set.add((line.x2(), line.y2()))
                elif isinstance(item, QGraphicsPathItem):
                    path = item.path()
                    for i in range(path.elementCount()):
                        e = path.elementAt(i)
                        points_set.add((e.x, e.y))
                elif isinstance(item, QGraphicsEllipseItem):
                    rect = item.rect()
                    cx = rect.center().x()
                    cy = rect.center().y()
                    r = rect.width() / 2
                    points_set.add((cx + r, cy))
                    points_set.add((cx - r, cy))

            points_list = [(round(p[0], 3), round(p[1], 3)) for p in points_set]
            points_list = [p for p in points_list if not (abs(p[0]) < 0.01 and abs(p[1]) < 0.01)]
            self.trace_points = points_list
            print(f"Точки трассировки загружены: {self.trace_points}")

            # Пересчитаем trace_points сразу — чтобы они были готовы! self.trace_points = [ (round(x, 2), round(y, 2)) for (x, y) in self.trace_points ]

            self.graphics_view.setScene(self.scene)

            self.graphics_view.setTransform(QTransform.fromScale(1, -1))
            self.graphics_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

            # Только теперь вызываем проверку трассы
            self.check_trace()


        except Exception as e:
            self.device_status_label.append(f"Ошибка DXF:\n{str(e)}")



    def init_ui(self):
        # Центральная сцена
        self.scene = QGraphicsScene()
        self.graphics_view = QGraphicsView(self.scene)
        self.graphics_view.setTransform(QTransform.fromScale(1, -1))

        # Верхний блок
        self.load_file_btn = QPushButton("Загрузить DXF")
        self.load_file_btn.clicked.connect(self.load_dxf_file)

        self.file_label = QLabel("Файл не выбран")
        self.check_trace_btn = QPushButton("Проверка трасс")
        self.check_trace_btn.clicked.connect(lambda: self.check_trace(manual=True))
        self.settings_btn = QPushButton("Настройки")
        self.settings_btn.clicked.connect(self.open_settings)
        self.log_btn = QPushButton("Логи")
        self.log_btn.clicked.connect(self.show_log_window)
        self.exit_btn = QPushButton("Выход")
        self.exit_btn.clicked.connect(self.confirm_exit)

        top_bar = QHBoxLayout()
        top_bar.addWidget(self.load_file_btn)
        top_bar.addWidget(self.file_label)
        top_bar.addStretch()
        top_bar.addWidget(self.check_trace_btn)
        top_bar.addWidget(self.settings_btn)
        top_bar.addWidget(self.log_btn)
        top_bar.addWidget(self.exit_btn)

        # Правая панель — кнопки управления и статусы
        self.start_btn = QPushButton("Старт")
        self.start_btn.clicked.connect(self.start_clicked)

        self.pause_btn = QPushButton("Пауза / Продолжить")
        self.pause_btn.clicked.connect(self.pause_resume_clicked)

        self.stop_btn = QPushButton("Стоп")
        self.stop_btn.clicked.connect(self.stop_clicked)

        right_controls = QVBoxLayout()
        right_controls.addWidget(self.start_btn)
        right_controls.addWidget(self.pause_btn)
        right_controls.addWidget(self.stop_btn)
        right_controls.addStretch()

        # Основной статус (состояние программы + подключение)
        self.status_label = QLabel("Статус: Ожидание\nArduino: Не подключено")
        right_controls.addWidget(self.status_label)

        # Статусы от Arduino
        right_controls.addWidget(QLabel("Статусы от Arduino:"))

        self.status_request_btn = QPushButton("Запросить статус контроллера")
        self.status_request_btn.clicked.connect(self.send_manual_status_request)
        right_controls.addWidget(self.status_request_btn)

        self.device_status_label = QTextEdit()
        self.device_status_label.setReadOnly(True)
        self.device_status_label.setPlaceholderText("Статусы от Arduino...")
        self.device_status_label.setFixedHeight(200)  # увеличено
        self.device_status_label.setLineWrapMode(QTextEdit.WidgetWidth)
        right_controls.addWidget(self.device_status_label)

        # Обертка правой панели
        right_panel = QWidget()
        right_panel.setLayout(right_controls)
        right_panel.setFixedWidth(250)

        # Нижняя панель — индикатор прогресса
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_label = QLabel("0% - Осталось: 0:00")

        bottom_bar = QHBoxLayout()
        bottom_bar.addWidget(self.progress_bar)
        bottom_bar.addWidget(self.progress_label)

        # Компоновка центральной части
        center_layout = QHBoxLayout()
        center_layout.addWidget(self.graphics_view)
        center_layout.addWidget(right_panel)

        # Общая компоновка
        main_layout = QVBoxLayout()
        main_layout.addLayout(top_bar)
        main_layout.addLayout(center_layout)
        main_layout.addLayout(bottom_bar)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        self.already_ready = False



    def open_settings(self):
        dlg = SettingsDialog(self)
        try:
            self.curve_step = float(dlg.curve_step_input.text())
        except ValueError:
            self.curve_step = 1.0  # значение по умолчанию
        
        if dlg.exec_():
            self.node_tolerance = dlg.get_node_tolerance()
            new_serial = dlg.get_serial_connection()

            # Только если выбрали COM-порт — обновляем self.serial
            if new_serial:
                self.serial = new_serial

            self.speed = int(dlg.speed_input.text())
            self.steps_per_meter_x = int(dlg.steps_per_meter_x_input.text())
            self.steps_per_meter_y = int(dlg.steps_per_meter_y_input.text())
            self.invert_x = dlg.invert_x_box.currentIndex()
            self.invert_y = dlg.invert_y_box.currentIndex()

            if self.serial:
                self.status_label.setText("Статус: Ожидание\nArduino: Подключено")

        self.show_delay_markers = dlg.show_delay_markers_box.currentIndex() == 1
        try:
            self.delay_time = int(dlg.delay_time_input.text())
        except ValueError:
            self.delay_time = 500
        try:
            self.delay_angle_threshold = int(dlg.delay_angle_threshold_input.text())
        except ValueError:
            self.delay_angle_threshold = 170





          
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
