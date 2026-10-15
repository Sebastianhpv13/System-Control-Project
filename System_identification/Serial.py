import serial
import time
import matplotlib.pyplot as plt

PUERTO = 'COM12'

ser = serial.Serial(PUERTO, 9600)
time.sleep(2)

tiempos = []
valores = []

plt.ion()
fig, ax = plt.subplots()

print("Graficando y guardando datos...")
print("Presiona Ctrl+C en la consola para detener.")

with open('datos_analogicos.csv', 'w') as archivo:
    archivo.write("Tiempo_s,Valor_invertido\n")

    try:
        while True:
            linea = ser.readline().decode('utf-8').strip()
            partes = linea.split(',')

            if len(partes) == 2:
                try:
                    t = float(partes[0])
                    adc = float(partes[1])

                    # Invertir ADC:
                    # ADC alto = frío
                    # ADC bajo = caliente
                    valor = 1023 - adc

                    tiempos.append(t)
                    valores.append(valor)

                    archivo.write(f"{t},{valor}\n")
                    archivo.flush()

                    ax.clear()
                    ax.plot(tiempos, valores, 'r-')

                    ax.set_title("Respuesta Térmica en Lazo Abierto")
                    ax.set_xlabel("Tiempo (segundos)")
                    ax.set_ylabel("Respuesta del sensor")
                    ax.grid(True)

                    plt.pause(0.01)

                except ValueError:
                    print(f"Dato inválido: {linea}")

    except KeyboardInterrupt:
        print("\nPrueba terminada.")
        print("Datos guardados en 'datos_analogicos.csv'.")

    finally:
        ser.close()
        plt.ioff()
        plt.show()