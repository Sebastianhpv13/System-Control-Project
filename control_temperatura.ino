const int PIN_PWM_TIP = 6;     
const int PIN_NTC = A0;        

const float R_DIVISOR = 10000.0;       
const float NOMINAL_RESISTANCE = 10000.0; 
const float NOMINAL_TEMPERATURE = 25.0;  
const float B_COEFFICIENT = 3950.0;      

float Kp = 6.0;   
float Ki = 0.15;  
float Kd = 0.0;   

float setpoint = 35.0;
float tempActual = 0.0;
float pwmSalida = 0.0;
bool sistemaActivo = false;

float errorAcumulado = 0.0;
unsigned long ultimoTiempo = 0;

float leerTemperatura();
void escucharSerie();

void setup() {
  Serial.begin(9600);
  pinMode(PIN_PWM_TIP, OUTPUT);
  analogWrite(PIN_PWM_TIP, 0); 
  ultimoTiempo = millis();
}

void loop() {
  escucharSerie();

  unsigned long tiempoActual = millis();
  if (tiempoActual - ultimoTiempo >= 100) { 
    float dt = (tiempoActual - ultimoTiempo) / 1000.0; 
    ultimoTiempo = tiempoActual;

    tempActual = leerTemperatura();

    if (sistemaActivo && tempActual > -5.0 && tempActual < 110.0) {
      float error = setpoint - tempActual;

      if (abs(error) < 5.0) {
        errorAcumulado += (error * dt);
        errorAcumulado = constrain(errorAcumulado, -50.0, 50.0);
      } else {
        errorAcumulado = 0.0; 
      }

      float calculoPI = (Kp * error) + (Ki * errorAcumulado);

      pwmSalida = constrain(calculoPI, 0.0, 255.0);
    } else {
      pwmSalida = 0.0;
      errorAcumulado = 0.0;
    }

    analogWrite(PIN_PWM_TIP, (int)pwmSalida);

    Serial.print(tiempoActual / 1000.0, 1);
    Serial.print(",");
    Serial.print(tempActual, 2);
    Serial.print(",");
    Serial.print(setpoint, 1);
    Serial.print(",");
    Serial.print(pwmSalida, 1);
    Serial.println(",0");
  }
}

float leerTemperatura() {
  long sumaADC = 0;
  for (int i = 0; i < 15; i++) { 
    sumaADC += analogRead(PIN_NTC);
    delayMicroseconds(100);
  }
  float rawADC = sumaADC / 15.0;

  if (rawADC <= 5) return -10.0;    
  if (rawADC >= 1018) return 100.0;  

  float resistencia = R_DIVISOR * ((1023.0 - rawADC) / rawADC);

  float steinhart;
  steinhart = resistencia / NOMINAL_RESISTANCE;
  steinhart = log(steinhart);
  steinhart /= B_COEFFICIENT;
  steinhart += 1.0 / (NOMINAL_TEMPERATURE + 273.15);
  steinhart = 1.0 / steinhart;
  steinhart -= 273.15;

  return steinhart;
}

void escucharSerie() {
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();

    if (comando == "START") {
      sistemaActivo = true;
      errorAcumulado = 0.0;
    } else if (comando == "STOP") {
      sistemaActivo = false;
      analogWrite(PIN_PWM_TIP, 0);
    } else if (comando.startsWith("SET:")) {
      setpoint = comando.substring(4).toFloat();
    }
  }
}
