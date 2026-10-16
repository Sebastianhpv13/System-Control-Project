const int PIN_MOSFET = 6;      // Pin 6 (PWM)
const int PIN_TERMISTOR = A0;

unsigned long tiempoInicio = 0;
bool sistemaActivo = false;

// PWM = 30 (~12% de potencia) para que la curva suba suavemente
// y alcance la meseta de estabilización entre 700 y 850 ADC.
const int POTENCIA_PWM = 30; 

void setup() {
  Serial.begin(9600);
  pinMode(PIN_MOSFET, OUTPUT);
  
  analogWrite(PIN_MOSFET, 0);  // Inicia apagado
  tiempoInicio = millis();     // Tiempo continuo
}

void loop() {
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();
    
    if (comando == "1" || comando == "START" || comando == "start") {
      analogWrite(PIN_MOSFET, POTENCIA_PWM); // Aplicar escalón bajo
      sistemaActivo = true;
    } 
    else if (comando == "0" || comando == "STOP" || comando == "stop") {
      analogWrite(PIN_MOSFET, 0);           // Apagar
      sistemaActivo = false;
    }
  }

  // Sobremuestreo de 20 lecturas rápidas para eliminar el ruido de conmutación
  long sumaADC = 0;
  for (int i = 0; i < 20; i++) {
    sumaADC += analogRead(PIN_TERMISTOR);
    delayMicroseconds(150);
  }
  float valorADC = sumaADC / 20.0;

  float tiempoSeg = (millis() - tiempoInicio) / 1000.0;

  // Transmisión directa a Python: Tiempo, ValorADC
  Serial.print(tiempoSeg, 2);
  Serial.print(",");
  Serial.println(valorADC, 1);

  delay(500); 
}
