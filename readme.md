# Sistema de Control de Temperatura en Bucle Cerrado (PI/PID)

## Descripcion General

Este proyecto implementa un sistema de control de temperatura en bucle cerrado (Closed-Loop) que combina adquisición de datos en hardware mediante Arduino y una interfaz de usuario interactiva en Python. 

El controlador ajusta continuamente la potencia entregada a un elemento calefactor mediante modulacion por ancho de pulso (PWM) para alcanzar y mantener una temperatura deseada (Setpoint), respondiendo de forma dinamica ante perturbaciones externas (como corrientes de aire) y permitiendo el analisis del tiempo muerto del sistema.

---

## Esquema del Circuito

El circuito esta dividido en dos secciones principales: lectura de sensor NTC y etapa de potencia para el elemento calefactor.

![Esquema del Circuito](https://raw.githubusercontent.com/username/repository/main/schematic.png)

### Componentes y Conexiones
1. **Etapa de Lectura (Termistor):**
   * Termistor NTC ($R_t = f(t)$) en configuracion de divisor de tension con resistencia de referencia $R_2 = 10\text{ k}\Omega$.
   * Punto de lectura conectado a la entrada analogica `A0` del Arduino.
2. **Etapa de Potencia (Calentador):**
   * Transistor NPN de potencia TIP120 o TIP122.
   * Resistencia de base $R_1 > 1\text{ k}\Omega$ conectada al pin de salida digital PWM del Arduino.
   * Elemento calefactor ($R_h$) alimentado externamente para evitar sobrecargas en la placa.
   * Tierra comun (GND) compartida entre la fuente externa y el Arduino.

---

## Caracteristicas de la Interfaz

* **Monitoreo en Tiempo Real:** Graficas simultaneas de Temperatura vs. Setpoint y de la Signal de Control PWM (PI/PID).
* **Ajuste Dinamico:** Perilla digital (Dial) para la seleccion continua de la temperatura objetivo.
* **Control Digital:** Boton de encendido y apagado de la etapa de potencia.
* **Marcadores de Evento:** Marcado automatico con lineas verticales en los instantes de cambio de Setpoint y Estado, facilitando el calculo experimental del tiempo muerto ($t_d$).
* **Exportacion de Datos:** Opcion de guardado del registro historico en formato CSV e imagenes de las graficas en PNG o PDF.

---

## Requisitos e Instalacion

### Hardware
* Arduino Nano / Uno.
* Transistor TIP120 o TIP122.
* Termistor NTC 10k.
* Resistencia $1\text{ k}\Omega$ y Resistencia $10\text{ k}\Omega$.
* Fuente de alimentacion externa de 5V.

### Dependencias de Software
Las dependencias requeridas se encuentran enlistadas en el archivo `requirements.txt`. Para instalarlas, ejecute:

```bash
python -m pip install -r requirements.txt
```

---

## Uso del Sistema

1. Cargar el codigo `control_temperatura.ino` en la placa Arduino.
2. Conectar el Arduino via USB a la computadora y energizar la fuente externa del calentador.
3. Ejecutar la aplicacion de Python:

```bash
python app_control.py
```

4. Seleccionar el puerto COM correspondiente, establecer la conexion y encender la etapa de potencia desde la interfaz visual.