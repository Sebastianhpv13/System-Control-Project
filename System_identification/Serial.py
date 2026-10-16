import sys
import os
import csv
import serial
import serial.tools.list_ports

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QLineEdit, QFileDialog, QMessageBox, QGroupBox
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class IdentificacionLazoAbiertoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Identificación Térmica - Lazo Abierto")
        self.resize(1100, 750)

        self.serial_port = None
        self.sistema_activo = False

        self.time_data = []
        self.adc_data = []
        self.events = []

        self.init_ui()

        # Timer para lectura del puerto serie (100 ms)
        self.timer_serial = QTimer()
        self.timer_serial.setInterval(100)
        self.timer_serial.timeout.connect(self.read_serial_data)

        # Timer para refresco suave de la gráfica (300 ms)
        self.timer_plot = QTimer()
        self.timer_plot.setInterval(300)
        self.timer_plot.timeout.connect(self.update_plots)

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e2e; }
            QGroupBox {
                color: #cdd6f4; font-weight: bold; font-size: 13px;
                border: 1px solid #45475a; border-radius: 8px; margin-top: 10px; padding-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }
            QLabel { color: #cdd6f4; }
            QPushButton {
                background-color: #313244; color: #cdd6f4; border: 1px solid #45475a;
                border-radius: 6px; padding: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: #45475a; }
            QComboBox, QLineEdit {
                background-color: #181825; color: #cdd6f4; border: 1px solid #45475a;
                border-radius: 5px; padding: 5px;
            }
        """)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout_principal = QHBoxLayout(main_widget)

        # Panel Izquierdo
        panel_control = QVBoxLayout()
        panel_control.setSpacing(12)

        # 1. Puerto Serie
        box_conexion = QGroupBox("Puerto Serie")
        layout_conexion = QVBoxLayout()
        self.combo_puertos = QComboBox()
        self.actualizar_puertos()
        layout_conexion.addWidget(self.combo_puertos)

        self.btn_conectar = QPushButton("⚡ Conectar Arduino")
        self.btn_conectar.setFixedHeight(35)
        self.btn_conectar.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold;")
        self.btn_conectar.clicked.connect(self.toggle_conexion)
        layout_conexion.addWidget(self.btn_conectar)
        box_conexion.setLayout(layout_conexion)
        panel_control.addWidget(box_conexion)

        # 2. Excitación (START / STOP)
        box_comando = QGroupBox("Control de Excitación")
        layout_comando = QVBoxLayout()

        self.btn_potencia = QPushButton("▶ APLICAR ESCALÓN (START)")
        self.btn_potencia.setFixedHeight(45)
        self.btn_potencia.setFont(QFont("Arial", 10, QFont.Bold))
        self.btn_potencia.setStyleSheet("background-color: #a6e3a1; color: #11111b;")
        self.btn_potencia.clicked.connect(self.toggle_potencia)
        layout_comando.addWidget(self.btn_potencia)

        lbl_cmd = QLabel("Comando manual:")
        layout_comando.addWidget(lbl_cmd)

        layout_input = QHBoxLayout()
        self.txt_comando = QLineEdit()
        self.txt_comando.setPlaceholderText("START o STOP")
        self.txt_comando.returnPressed.connect(self.enviar_comando_texto)
        layout_input.addWidget(self.txt_comando)

        self.btn_enviar = QPushButton("Enviar")
        self.btn_enviar.clicked.connect(self.enviar_comando_texto)
        layout_input.addWidget(self.btn_enviar)

        layout_comando.addLayout(layout_input)
        box_comando.setLayout(layout_comando)
        panel_control.addWidget(box_comando)

        # 3. Lectura ADC
        box_lecturas = QGroupBox("Lecturas en Tiempo Real")
        layout_lecturas = QVBoxLayout()

        self.lbl_raw_adc = QLabel("Lectura ADC (A0): --")
        self.lbl_raw_adc.setStyleSheet("color: #f38ba8; font-weight: bold; font-size: 16px;")
        layout_lecturas.addWidget(self.lbl_raw_adc)

        self.lbl_tiempo = QLabel("Tiempo: 0.0 s")
        self.lbl_tiempo.setStyleSheet("color: #f9e2af; font-size: 13px; font-weight: bold;")
        layout_lecturas.addWidget(self.lbl_tiempo)

        box_lecturas.setLayout(layout_lecturas)
        panel_control.addWidget(box_lecturas)

        panel_control.addStretch()

        # 4. Exportación
        box_export = QGroupBox("Opciones de Exportación")
        layout_export = QVBoxLayout()

        self.btn_csv = QPushButton("💾 Guardar CSV")
        self.btn_csv.clicked.connect(self.guardar_csv)
        layout_export.addWidget(self.btn_csv)

        self.btn_guardar_todo = QPushButton("📦 GUARDAR TODO (CSV + PNG)")
        self.btn_guardar_todo.setFixedHeight(38)
        self.btn_guardar_todo.setStyleSheet("background-color: #cba6f7; color: #11111b; font-weight: bold;")
        self.btn_guardar_todo.clicked.connect(self.guardar_todo)
        layout_export.addWidget(self.btn_guardar_todo)

        box_export.setLayout(layout_export)
        panel_control.addWidget(box_export)

        layout_principal.addLayout(panel_control, stretch=1)

        # Panel Derecho (Gráfica)
        self.figure = Figure(figsize=(7, 6), dpi=100, facecolor='#181825')
        self.canvas = FigureCanvas(self.figure)

        self.ax = self.figure.add_subplot(111)
        self.configurar_estilo_grafica()

        layout_principal.addWidget(self.canvas, stretch=3)

    def configurar_estilo_grafica(self):
        self.ax.set_facecolor('#11111b')
        self.ax.tick_params(colors='#cdd6f4', labelsize=10)
        self.ax.xaxis.label.set_color('#cdd6f4')
        self.ax.yaxis.label.set_color('#cdd6f4')
        self.ax.title.set_color('#cdd6f4')
        for spine in self.ax.spines.values():
            spine.set_color('#45475a')

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
                self.btn_conectar.setText("⛔ Desconectar")
                self.btn_conectar.setStyleSheet("background-color: #f38ba8; color: #11111b; font-weight: bold;")
                self.time_data.clear()
                self.adc_data.clear()
                self.events.clear()
                self.timer_serial.start()
                self.timer_plot.start()
            except Exception as e:
                QMessageBox.critical(self, "Error", "No se pudo conectar:\n" + str(e))
        else:
            self.timer_serial.stop()
            self.timer_plot.stop()
            if self.serial_port:
                self.serial_port.write(b"0\n")
                self.serial_port.close()
            self.serial_port = None
            self.btn_conectar.setText("⚡ Conectar Arduino")
            self.btn_conectar.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold;")

    def obtener_tiempo_actual(self):
        return self.time_data[-1] if self.time_data else 0.0

    def toggle_potencia(self):
        if self.serial_port and self.serial_port.is_open:
            t_ev = self.obtener_tiempo_actual()
            if not self.sistema_activo:
                self.sistema_activo = True
                self.serial_port.write(b"1\n")
                self.btn_potencia.setText("⏹ DETENER ESCALÓN (STOP)")
                self.btn_potencia.setStyleSheet("background-color: #f38ba8; color: #11111b;")
                self.events.append((t_ev, "START"))
            else:
                self.sistema_activo = False
                self.serial_port.write(b"0\n")
                self.btn_potencia.setText("▶ APLICAR ESCALÓN (START)")
                self.btn_potencia.setStyleSheet("background-color: #a6e3a1; color: #11111b;")
                self.events.append((t_ev, "STOP"))

    def enviar_comando_texto(self):
        cmd = self.txt_comando.text().strip()
        if cmd and self.serial_port and self.serial_port.is_open:
            self.serial_port.write((cmd + "\n").encode('utf-8'))
            t_ev = self.obtener_tiempo_actual()
            self.events.append((t_ev, "Cmd: " + cmd))

            if cmd in ["1", "START", "start"]:
                self.sistema_activo = True
                self.btn_potencia.setText("⏹ DETENER ESCALÓN (STOP)")
                self.btn_potencia.setStyleSheet("background-color: #f38ba8; color: #11111b;")
            elif cmd in ["0", "STOP", "stop"]:
                self.sistema_activo = False
                self.btn_potencia.setText("▶ APLICAR ESCALÓN (START)")
                self.btn_potencia.setStyleSheet("background-color: #a6e3a1; color: #11111b;")

            self.txt_comando.clear()

    def read_serial_data(self):
        if self.serial_port and self.serial_port.is_open:
            while self.serial_port.in_waiting > 0:
                try:
                    linea = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    partes = linea.split(',')
                    if len(partes) >= 2:
                        t = float(partes[0])
                        adc = float(partes[1])

                        self.time_data.append(t)
                        self.adc_data.append(adc)

                        self.lbl_raw_adc.setText("Lectura ADC (A0): " + str(int(adc)))
                        self.lbl_tiempo.setText("Tiempo: " + str(round(t, 1)) + " s")
                except ValueError:
                    pass

    def update_plots(self):
        if not self.time_data:
            return

        self.ax.clear()
        self.configurar_estilo_grafica()

        # Trazado de la respuesta ADC directa
        self.ax.plot(self.time_data, self.adc_data, color="#f38ba8", linewidth=2, label="Respuesta Térmica (ADC)")
        
        self.ax.set_title("Identificación de Sistemas: Respuesta al Escalón (Lazo Abierto)", fontsize=12, pad=12)
        self.ax.set_xlabel("Tiempo (s)", labelpad=8)
        self.ax.set_ylabel("Respuesta del Sensor (ADC)", labelpad=8)
        self.ax.grid(True, linestyle="--", alpha=0.3, color="#585b70")
        self.ax.legend(loc="upper left", facecolor="#181825", edgecolor="#45475a", labelcolor="#cdd6f4")

        y_min = min(self.adc_data) - 10
        y_max = max(self.adc_data) + 15
        self.ax.set_ylim(y_min, y_max)
        self.ax.set_xlim(0, max(self.time_data) + 2)

        # Líneas verticales de eventos
        for ev_t, ev_text in self.events:
            self.ax.axvline(x=ev_t, color='#cba6f7', linestyle='--', linewidth=1.5, alpha=0.8)
            ylim_top = self.ax.get_ylim()[1]
            self.ax.text(ev_t, ylim_top - (ylim_top*0.06), " " + ev_text, color='#cba6f7', rotation=90, fontweight='bold', fontsize=9)

        self.figure.tight_layout()
        self.canvas.draw()

    def guardar_csv(self):
        if not self.time_data:
            QMessageBox.information(self, "Aviso", "No hay datos para exportar.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Guardar CSV", "", "Archivos CSV (*.csv)")
        if path:
            try:
                with open(path, mode='w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Tiempo_s", "Valor_ADC"])
                    for i in range(len(self.time_data)):
                        writer.writerow([self.time_data[i], self.adc_data[i]])
                QMessageBox.information(self, "Éxito", "CSV guardado correctamente.")
            except Exception as e:
                QMessageBox.critical(self, "Error", "Error al guardar:\n" + str(e))

    def guardar_todo(self):
        if not self.time_data:
            QMessageBox.information(self, "Aviso", "No hay datos para exportar.")
            return

        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta para Guardar Todo")
        if folder:
            try:
                img_path = os.path.join(folder, "Grafica_Respuesta_Termica.png")
                self.figure.savefig(img_path, dpi=300, bbox_inches='tight', facecolor='#181825')

                csv_path = os.path.join(folder, "datos_analogicos.csv")
                with open(csv_path, mode='w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Tiempo_s", "Valor_ADC"])
                    for i in range(len(self.time_data)):
                        writer.writerow([self.time_data[i], self.adc_data[i]])

                QMessageBox.information(self, "Éxito", "¡Paquete completo guardado en:\n" + folder)
            except Exception as e:
                QMessageBox.critical(self, "Error", "Error al guardar paquete:\n" + str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = IdentificacionLazoAbiertoApp()
    ventana.show()
    sys.exit(app.exec_())
