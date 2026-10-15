import sys
import csv
import time
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QDial, QFileDialog, QComboBox, QMessageBox
)
from PyQt5.QtCore import QTimer, Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class InterfaceControlTemperatura(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Control de Temperatura - PID Cerrado")
        self.resize(1000, 750)

        # Conexion Serial
        self.ser = None

        # Almacenamiento de datos
        self.time_data = []
        self.temp_data = []
        self.setpoint_data = []
        self.pwm_data = []
        self.events = []  # Estructura: (tiempo, texto_evento, valor_y)

        self.start_time = None
        self.is_running = False

        self.init_ui()

        # Timer para lectura y actualizacion de graficas (10 Hz)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_loop)
        self.timer.start(100)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # --- PANEL DE CONTROL IZQUIERDO ---
        control_panel = QVBoxLayout()

        # Seleccion de Puerto Serial
        control_panel.addWidget(QLabel("<b>Puerto Serial:</b>"))
        self.cb_ports = QComboBox()
        self.refresh_ports()
        control_panel.addWidget(self.cb_ports)

        self.btn_connect = QPushButton("Conectado / Desconectado")
        self.btn_connect.setCheckable(True)
        self.btn_connect.clicked.connect(self.toggle_connection)
        control_panel.addWidget(self.btn_connect)

        control_panel.addSpacing(15)

        # Boton Encendido / Apagado Digital
        self.btn_power = QPushButton("ENCENDER SISTEMA")
        self.btn_power.setStyleSheet("background-color: green; color: white; font-weight: bold; padding: 10px;")
        self.btn_power.setCheckable(True)
        self.btn_power.clicked.connect(self.toggle_power)
        control_panel.addWidget(self.btn_power)

        control_panel.addSpacing(20)

        # Perilla (Dial) para Setpoint de Temperatura
        control_panel.addWidget(QLabel("<b>Ajuste de Temperatura (°C):</b>"))
        self.dial = QDial()
        self.dial.setRange(20, 80)
        self.dial.setValue(35)
        self.dial.setNotchesVisible(True)
        self.dial.valueChanged.connect(self.on_dial_change)
        control_panel.addWidget(self.dial)

        self.lbl_setpoint = QLabel("Setpoint: 35.0 °C")
        self.lbl_setpoint.setAlignment(Qt.AlignCenter)
        self.lbl_setpoint.setStyleSheet("font-size: 16px; font-weight: bold;")
        control_panel.addWidget(self.lbl_setpoint)

        control_panel.addSpacing(20)

        # Lecturas en Tiempo Real
        self.lbl_temp_now = QLabel("Temp Actual: -- °C")
        self.lbl_temp_now.setStyleSheet("font-size: 14px; color: blue;")
        control_panel.addWidget(self.lbl_temp_now)

        self.lbl_pwm_now = QLabel("Respuesta PWM (PI/PID): -- %")
        self.lbl_pwm_now.setStyleSheet("font-size: 14px; color: red;")
        control_panel.addWidget(self.lbl_pwm_now)

        control_panel.addStretch()

        # Botones de Guardado
        self.btn_save_csv = QPushButton("Guardar Datos (CSV)")
        self.btn_save_csv.clicked.connect(self.save_csv)
        control_panel.addWidget(self.btn_save_csv)

        self.btn_save_plot = QPushButton("Guardar Graficas (Imagen)")
        self.btn_save_plot.clicked.connect(self.save_plot)
        control_panel.addWidget(self.btn_save_plot)

        # --- PANEL DE GRAFICAS DERECHO ---
        plot_panel = QVBoxLayout()
        self.figure, (self.ax_temp, self.ax_pid) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        self.canvas = FigureCanvas(self.figure)
        plot_panel.addWidget(self.canvas)

        main_layout.addLayout(control_panel, 1)
        main_layout.addLayout(plot_panel, 3)

    def refresh_ports(self):
        self.cb_ports.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self.cb_ports.addItem(p.device)

    def toggle_connection(self):
        if self.btn_connect.isChecked():
            port = self.cb_ports.currentText()
            if not port:
                QMessageBox.warning(self, "Error", "No se selecciono un puerto valido.")
                self.btn_connect.setChecked(False)
                return
            try:
                self.ser = serial.Serial(port, 9600, timeout=0.1)
                self.btn_connect.setText("Desconectar")
                self.start_time = time.time()
            except Exception as e:
                QMessageBox.critical(self, "Error de conexion", str(e))
                self.btn_connect.setChecked(False)
        else:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.btn_connect.setText("Conectar")

    def toggle_power(self):
        if not self.ser or not self.ser.is_open:
            QMessageBox.warning(self, "Advertencia", "Conectese al puerto Serial primero.")
            self.btn_power.setChecked(False)
            return

        t_curr = time.time() - self.start_time if self.start_time else 0
        if self.btn_power.isChecked():
            self.btn_power.setText("APAGAR SISTEMA")
            self.btn_power.setStyleSheet("background-color: red; color: white; font-weight: bold; padding: 10px;")
            self.ser.write(b"START\n")
            self.events.append((t_curr, "ON", self.dial.value()))
        else:
            self.btn_power.setText("ENCENDER SISTEMA")
            self.btn_power.setStyleSheet("background-color: green; color: white; font-weight: bold; padding: 10px;")
            self.ser.write(b"STOP\n")
            self.events.append((t_curr, "OFF", 0))

    def on_dial_change(self, value):
        val_float = float(value)
        self.lbl_setpoint.setText(f"Setpoint: {val_float:.1f} °C")
        if self.ser and self.ser.is_open:
            self.ser.write(f"SET:{val_float}\n".encode())
            t_curr = time.time() - self.start_time if self.start_time else 0
            self.events.append((t_curr, f"Set:{val_float}°C", val_float))

    def update_loop(self):
        if self.ser and self.ser.is_open and self.ser.in_waiting:
            try:
                line = self.ser.readline().decode('utf-8').strip()
                parts = line.split(',')
                if len(parts) == 5:
                    t_val = float(parts[0])
                    temp_val = float(parts[1])
                    sp_val = float(parts[2])
                    pwm_val = float(parts[3])

                    self.time_data.append(t_val)
                    self.temp_data.append(temp_val)
                    self.setpoint_data.append(sp_val)
                    self.pwm_data.append(pwm_val)

                    self.lbl_temp_now.setText(f"Temp Actual: {temp_val:.2f} °C")
                    self.lbl_pwm_now.setText(f"Respuesta PWM (PI/PID): {(pwm_val/255.0)*100:.1f} %")

                    self.update_plots()
            except Exception:
                pass

    def update_plots(self):
        self.ax_temp.clear()
        self.ax_pid.clear()

        # Grafica 1: Temperatura y Setpoint
        self.ax_temp.plot(self.time_data, self.temp_data, label="Temp Medida (°C)", color="blue", linewidth=1.5)
        self.ax_temp.plot(self.time_data, self.setpoint_data, label="Setpoint (°C)", color="orange", linestyle="--", linewidth=1.5)
        self.ax_temp.set_ylabel("Temperatura (°C)")
        self.ax_temp.set_title("Respuesta de Temperatura y Setpoint")
        self.ax_temp.grid(True)
        self.ax_temp.legend(loc="upper left")

        # Marcar eventos (ON, OFF, Cambios de Setpoint) para calculo de tiempo muerto
        for ev_t, ev_text, ev_val in self.events:
            self.ax_temp.axvline(x=ev_t, color='purple', linestyle=':', alpha=0.7)
            self.ax_temp.text(ev_t, self.ax_temp.get_ylim()[0] + 1, f" {ev_text}", color='purple', rotation=90, fontweight='bold')

        # Grafica 2: Reaccion del PID (PWM de Salida / Calentamiento)
        self.ax_pid.plot(self.time_data, self.pwm_data, label="Salida Control PWM (0-255)", color="red", linewidth=1.2)
        self.ax_pid.set_xlabel("Tiempo (s)")
        self.ax_pid.set_ylabel("PWM (0 - 255)")
        self.ax_pid.set_title("Accion del Controlador PI/PID (Efecto del soplo/perturbacion)")
        self.ax_pid.grid(True)
        self.ax_pid.legend(loc="upper left")

        self.figure.tight_layout()
        self.canvas.draw()

    def save_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar Datos CSV", "", "CSV Files (*.csv)")
        if path:
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Tiempo(s)", "Temperatura(C)", "Setpoint(C)", "PWM(0-255)"])
                for row in zip(self.time_data, self.temp_data, self.setpoint_data, self.pwm_data):
                    writer.writerow(row)
            QMessageBox.information(self, "Exito", "Datos exportados correctamente.")

    def save_plot(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar Graficas", "", "PNG Image (*.png);;PDF File (*.pdf)")
        if path:
            self.figure.savefig(path)
            QMessageBox.information(self, "Exito", "Grafica guardada exitosamente.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = InterfaceControlTemperatura()
    window.show()
    sys.exit(app.exec_())