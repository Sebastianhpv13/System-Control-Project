import sys
import os
import csv
import time
import serial
import serial.tools.list_ports

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QDial, QFileDialog, QMessageBox, QGroupBox
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class ControlTemperaturaApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Control de Temperatura - PI Cerrado")
        self.resize(1120, 780)

        self.serial_port = None
        self.sistema_activo = False
        self.setpoint_actual = 35.0

        self.time_data = []
        self.temp_data = []
        self.setpoint_data = []
        self.pwm_data = []
        self.events = []  

        self.init_ui()

        self.timer_serial = QTimer()
        self.timer_serial.setInterval(100)
        self.timer_serial.timeout.connect(self.read_serial_data)

        self.timer_plot = QTimer()
        self.timer_plot.setInterval(333)
        self.timer_plot.timeout.connect(self.update_plots)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout_principal = QHBoxLayout(main_widget)

        panel_control = QVBoxLayout()

        lbl_puerto = QLabel("Puerto Serial:")
        lbl_puerto.setFont(QFont("Arial", 10, QFont.Bold))
        panel_control.addWidget(lbl_puerto)

        self.combo_puertos = QComboBox()
        self.actualizar_puertos()
        panel_control.addWidget(self.combo_puertos)

        self.btn_conectar = QPushButton("Conectar")
        self.btn_conectar.clicked.connect(self.toggle_conexion)
        panel_control.addWidget(self.btn_conectar)

        panel_control.addSpacing(10)

        self.btn_potencia = QPushButton("ENCENDER SISTEMA")
        self.btn_potencia.setFixedHeight(40)
        self.btn_potencia.setFont(QFont("Arial", 10, QFont.Bold))
        self.btn_potencia.setStyleSheet("background-color: green; color: white;")
        self.btn_potencia.clicked.connect(self.toggle_potencia)
        panel_control.addWidget(self.btn_potencia)

        panel_control.addSpacing(10)

        lbl_dial = QLabel("Ajuste de Temperatura (°C):")
        lbl_dial.setFont(QFont("Arial", 10, QFont.Bold))
        lbl_dial.setAlignment(Qt.AlignCenter)
        panel_control.addWidget(lbl_dial)

        layout_dial = QHBoxLayout()
        self.dial_setpoint = QDial()
        self.dial_setpoint.setFixedSize(160, 160)  
        self.dial_setpoint.setRange(20, 90)
        self.dial_setpoint.setValue(int(self.setpoint_actual))
        self.dial_setpoint.setNotchesVisible(True)
        self.dial_setpoint.valueChanged.connect(self.on_setpoint_change)
        layout_dial.addWidget(self.dial_setpoint, alignment=Qt.AlignCenter)
        panel_control.addLayout(layout_dial)

        self.lbl_setpoint_val = QLabel(f"Setpoint: {self.setpoint_actual:.1f} °C")
        self.lbl_setpoint_val.setAlignment(Qt.AlignCenter)
        self.lbl_setpoint_val.setFont(QFont("Arial", 11, QFont.Bold))
        panel_control.addWidget(self.lbl_setpoint_val)

        panel_control.addSpacing(10)

        self.lbl_temp_actual = QLabel("Temp Actual: -- °C")
        self.lbl_temp_actual.setStyleSheet("color: blue; font-weight: bold; font-size: 13px;")
        panel_control.addWidget(self.lbl_temp_actual)

        self.lbl_pwm_actual = QLabel("Respuesta PWM (PI): -- %")
        self.lbl_pwm_actual.setStyleSheet("color: red; font-weight: bold; font-size: 13px;")
        panel_control.addWidget(self.lbl_pwm_actual)

        panel_control.addStretch()

        box_export = QGroupBox("Opciones de Guardado")
        layout_export = QVBoxLayout()

        self.btn_img_temp = QPushButton("Guardar Gráfica de Temperatura")
        self.btn_img_temp.clicked.connect(self.guardar_imagen_temp)
        layout_export.addWidget(self.btn_img_temp)

        self.btn_csv = QPushButton("Guardar CSV")
        self.btn_csv.clicked.connect(self.guardar_csv)
        layout_export.addWidget(self.btn_csv)

        self.btn_guardar_todo = QPushButton("GUARDAR TODO")
        self.btn_guardar_todo.setFixedHeight(35)
        self.btn_guardar_todo.setStyleSheet("background-color: #2c3e50; color: white; font-weight: bold;")
        self.btn_guardar_todo.clicked.connect(self.guardar_todo)
        layout_export.addWidget(self.btn_guardar_todo)

        box_export.setLayout(layout_export)
        panel_control.addWidget(box_export)

        layout_principal.addLayout(panel_control, stretch=1)

        self.figure = Figure(figsize=(7, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)

        self.ax_temp = self.figure.add_subplot(211)
        self.ax_pid = self.figure.add_subplot(212)

        layout_principal.addWidget(self.canvas, stretch=3)

    def actualizar_puertos(self):
        self.combo_puertos.clear()
        puertos = serial.tools.list_ports.comports()
        for p in puertos:
            self.combo_puertos.addItem(p.device)

    def toggle_conexion(self):
        if self.serial_port is None or not self.serial_port.is_open:
            puerto = self.combo_puertos.currentText()
            if not puerto:
                QMessageBox.warning(self, "Error", "No hay puertos COM disponibles.")
                return
            try:
                self.serial_port = serial.Serial(puerto, 9600, timeout=0.1)
                self.btn_conectar.setText("Desconectar")
                self.btn_conectar.setStyleSheet("background-color: lightblue;")
                self.time_data.clear()
                self.temp_data.clear()
                self.setpoint_data.clear()
                self.pwm_data.clear()
                self.events.clear()
                self.timer_serial.start()
                self.timer_plot.start()
            except Exception as e:
                QMessageBox.critical(self, "Error de Conexión", f"No se pudo abrir el puerto:\n{str(e)}")
        else:
            self.timer_serial.stop()
            self.timer_plot.stop()
            if self.serial_port:
                self.serial_port.write(b"STOP\n")
                self.serial_port.close()
            self.serial_port = None
            self.btn_conectar.setText("Conectar")
            self.btn_conectar.setStyleSheet("")

    def obtener_tiempo_actual_arduino(self):
        if self.time_data:
            return self.time_data[-1]
        return 0.0

    def toggle_potencia(self):
        if self.serial_port and self.serial_port.is_open:
            t_event = self.obtener_tiempo_actual_arduino()
            if not self.sistema_activo:
                self.sistema_activo = True
                self.serial_port.write(b"START\n")
                self.btn_potencia.setText("APAGAR SISTEMA")
                self.btn_potencia.setStyleSheet("background-color: red; color: white;")
                self.events.append((t_event, "ON"))
            else:
                self.sistema_activo = False
                self.serial_port.write(b"STOP\n")
                self.btn_potencia.setText("ENCENDER SISTEMA")
                self.btn_potencia.setStyleSheet("background-color: green; color: white;")
                self.events.append((t_event, "OFF"))

    def on_setpoint_change(self, val):
        self.setpoint_actual = float(val)
        self.lbl_setpoint_val.setText(f"Setpoint: {self.setpoint_actual:.1f} °C")
        if self.serial_port and self.serial_port.is_open:
            cmd = f"SET:{self.setpoint_actual:.1f}\n"
            self.serial_port.write(cmd.encode('utf-8'))
            t_event = self.obtener_tiempo_actual_arduino()
            self.events.append((t_event, f"Set:{self.setpoint_actual:.1f}°C"))

    def read_serial_data(self):
        if self.serial_port and self.serial_port.is_open:
            while self.serial_port.in_waiting > 0:
                try:
                    linea = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    partes = linea.split(',')
                    if len(partes) >= 4:
                        t = float(partes[0])
                        temp = float(partes[1])
                        sp = float(partes[2])
                        pwm = float(partes[3])

                        self.time_data.append(t)
                        self.temp_data.append(temp)
                        self.setpoint_data.append(sp)
                        self.pwm_data.append(pwm)

                        self.lbl_temp_actual.setText(f"Temp Actual: {temp:.2f} °C")
                        pct_pwm = (pwm / 255.0) * 100.0
                        self.lbl_pwm_actual.setText(f"Respuesta PWM (PI): {pct_pwm:.1f} %")
                except ValueError:
                    pass

    def update_plots(self):
        if not self.time_data:
            return

        self.ax_temp.clear()
        self.ax_pid.clear()

        t_all = self.time_data
        temp_all = self.temp_data
        sp_all = self.setpoint_data
        pwm_all = self.pwm_data

        self.ax_temp.plot(t_all, temp_all, label="Temp Medida (°C)", color="blue", linewidth=1.5)
        self.ax_temp.plot(t_all, sp_all, label="Setpoint (°C)", color="orange", linestyle="--", linewidth=1.5)
        self.ax_temp.set_ylabel("Temperatura (°C)")
        self.ax_temp.set_title("Respuesta de Temperatura y Setpoint")
        self.ax_temp.grid(True)
        self.ax_temp.legend(loc="upper left")

        y_min = min(min(temp_all), min(sp_all)) - 5
        y_max = max(max(temp_all), max(sp_all)) + 10
        self.ax_temp.set_ylim(y_min, y_max)
        self.ax_temp.set_xlim(0, max(t_all) + 2)

        for ev_t, ev_text in self.events:
            self.ax_temp.axvline(x=ev_t, color='purple', linestyle=':', alpha=0.8)
            ylim_top = self.ax_temp.get_ylim()[1]
            self.ax_temp.text(ev_t, ylim_top - 8, f" {ev_text}", color='purple', rotation=90, fontweight='bold', fontsize=8)

        self.ax_pid.plot(t_all, pwm_all, label="Salida Control PWM PI (0-255)", color="red", linewidth=1.2)
        self.ax_pid.set_xlabel("Tiempo (s)")
        self.ax_pid.set_ylabel("PWM (0 - 255)")
        self.ax_pid.set_ylim(-10, 270)
        self.ax_pid.set_xlim(0, max(t_all) + 2)
        self.ax_pid.set_title("Acción Proporcional-Integral (PWM)")
        self.ax_pid.grid(True)
        self.ax_pid.legend(loc="upper left")

        self.figure.tight_layout()
        self.canvas.draw()

    def guardar_csv(self):
        if not self.time_data:
            QMessageBox.information(self, "Aviso", "No hay datos grabados para exportar.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Guardar Historial CSV", "", "Archivos CSV (*.csv)")
        if path:
            try:
                with open(path, mode='w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Tiempo_s", "Temperatura_C", "Setpoint_C", "PWM_0_255"])
                    for i in range(len(self.time_data)):
                        writer.writerow([self.time_data[i], self.temp_data[i], self.setpoint_data[i], self.pwm_data[i]])
                QMessageBox.information(self, "Éxito", "Archivo CSV guardado correctamente.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Falló al guardar el archivo CSV:\n{str(e)}")

    def guardar_imagen_temp(self):
        if not self.time_data:
            QMessageBox.information(self, "Aviso", "No hay datos de gráfica para guardar.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Guardar Gráfica de Temperatura", "", "PNG (*.png);;PDF (*.pdf)")
        if path:
            try:
                extent = self.ax_temp.get_tightbbox(self.figure.canvas.get_renderer()).transformed(self.figure.dpi_scale_trans.inverted())
                self.figure.savefig(path, bbox_inches=extent.expanded(1.15, 1.15), dpi=300)
                QMessageBox.information(self, "Éxito", "Gráfica de Temperatura guardada correctamente.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Falló al guardar la imagen:\n{str(e)}")

    def guardar_todo(self):
        if not self.time_data:
            QMessageBox.information(self, "Aviso", "No hay datos grabados para exportar.")
            return

        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta para Guardar Todo")
        if folder:
            try:
                renderer = self.figure.canvas.get_renderer()

                extent_temp = self.ax_temp.get_tightbbox(renderer).transformed(self.figure.dpi_scale_trans.inverted())
                self.figure.savefig(os.path.join(folder, "Temperatura.png"), bbox_inches=extent_temp.expanded(1.15, 1.15), dpi=300)

                extent_pwm = self.ax_pid.get_tightbbox(renderer).transformed(self.figure.dpi_scale_trans.inverted())
                self.figure.savefig(os.path.join(folder, "PWM.png"), bbox_inches=extent_pwm.expanded(1.15, 1.15), dpi=300)

                self.figure.savefig(os.path.join(folder, "Graficas_Combinadas.png"), dpi=300)

                csv_path = os.path.join(folder, "Historial_Datos.csv")
                with open(csv_path, mode='w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Tiempo_s", "Temperatura_C", "Setpoint_C", "PWM_0_255"])
                    for i in range(len(self.time_data)):
                        writer.writerow([self.time_data[i], self.temp_data[i], self.setpoint_data[i], self.pwm_data[i]])

                QMessageBox.information(
                    self, "Éxito",
                    f"¡Paquete completo guardado con éxito en:\n{folder}\n\nArchivos generados:\n- Temperatura.png\n- PWM.png\n- Graficas_Combinadas.png\n- Historial_Datos.csv"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Falló al guardar la prueba:\n{str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = ControlTemperaturaApp()
    ventana.show()
    sys.exit(app.exec_())
