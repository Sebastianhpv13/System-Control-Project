const int PIN_MOSFET = 7;
const int PIN_TERMISTOR = A0;

unsigned long tiempoInicio = 0;
bool sistemaActivo = false;

void setup() {
  Serial.begin(9600);
  pinMode(PIN_MOSFET, OUTPUT);
  
  digitalWrite(PIN_MOSFET, LOW);
  tiempoInicio = millis();
}

void loop() {
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();
    
    if (comando == "1" || comando == "START" || comando == "start") {
      digitalWrite(PIN_MOSFET, HIGH);
      sistemaActivo = true;
      tiempoInicio = millis();
    } 
    else if (comando == "0" || comando == "STOP" || comando == "stop") {
      digitalWrite(PIN_MOSFET, LOW);
      sistemaActivo = false;
    }
  }

  int valorADC = analogRead(PIN_TERMISTOR);
  float tiempoSeg = (millis() - tiempoInicio) / 1000.0;

  Serial.print(tiempoSeg);
  Serial.print(",");
  Serial.println(valorADC);

  delay(500); 
}