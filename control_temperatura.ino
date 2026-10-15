// Pines de hardware basados en el esquematico
const int PIN_SENSOR = A0;   // Lectura del termistor
const int PIN_HEATER = 6;    // Salida PWM hacia la base del transistor (TIP120/122)

// Parametros del sensor NTC (Ajustar segun el termistor)
const float R_DIVISOR = 10000.0; // Resistencia R2 (ej. 10k)
const float NOMINAL_RESISTANCE = 10000.0;
const float NOMINAL_TEMPERATURE = 25.0;
const float B_COEFFICIENT = 3950.0;

// Variables de Control PID
float setpoint = 35.0;     // Temperatura objetivo inicial (°C)
bool sistema_activo = false;

float Kp = 15.0;  // Ganancia Proporcional
float Ki = 0.5;   // Ganancia Integral
float Kd = 2.0;   // Ganancia Derivativa

float integral = 0.0;
float last_error = 0.0;
unsigned long last_time = 0;

void setup() {
  Serial.begin(9600);
  pinMode(PIN_HEATER, OUTPUT);
  analogWrite(PIN_HEATER, 0);
  last_time = millis();
}

float leerTemperatura() {
  int rawADC = analogRead(PIN_SENSOR);
  if (rawADC == 0) return 0.0;
  
  // Calculo de la resistencia del termistor (Divisor de voltaje)
  float resistencia = R_DIVISOR * ((1023.0 / rawADC) - 1.0);
  
  // Ecuacion de Beta / Steinhart-Hart simplificada
  float steinhart;
  steinhart = resistencia / NOMINAL_RESISTANCE;     // (R/Ro)
  steinhart = log(steinhart);                         // ln(R/Ro)
  steinhart /= B_COEFFICIENT;                         // 1/B * ln(R/Ro)
  steinhart += 1.0 / (NOMINAL_TEMPERATURE + 273.15); // + (1/To)
  steinhart = 1.0 / steinhart;                        // Invertir
  steinhart -= 273.15;                                // Convertir a Kelvin a °C
  
  return steinhart;
}

void loop() {
  // 1. Lectura de comandos desde Python por Serial
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();
    
    if (comando.startsWith("START")) {
      sistema_activo = true;
      integral = 0.0; // Resetear accion integral
    } else if (comando.startsWith("STOP")) {
      sistema_activo = false;
      analogWrite(PIN_HEATER, 0);
    } else if (comando.startsWith("SET:")) {
      setpoint = comando.substring(4).toFloat();
    }
  }

  // 2. Ciclo de control cada 100 ms
  unsigned long now = millis();
  float dt = (now - last_time) / 1000.0;

  if (dt >= 0.1) {
    float temp_actual = leerTemperatura();
    float pwm_out = 0.0;

    if (sistema_activo) {
      float error = setpoint - temp_actual;
      integral += error * dt;
      
      // Anti-windup (limitar accion integral)
      integral = constrain(integral, -100.0, 100.0);
      
      float derivative = (error - last_error) / dt;
      
      float output = (Kp * error) + (Ki * integral) + (Kd * derivative);
      pwm_out = constrain(output, 0, 255);
      
      analogWrite(PIN_HEATER, (int)pwm_out);
      last_error = error;
    } else {
      analogWrite(PIN_HEATER, 0);
      pwm_out = 0.0;
    }

    // 3. Enviar datos a Python: Tiempo(s), TempActual, Setpoint, PWM, Estado
    Serial.print(now / 1000.0, 2);
    Serial.print(",");
    Serial.print(temp_actual, 2);
    Serial.print(",");
    Serial.print(setpoint, 2);
    Serial.print(",");
    Serial.print(pwm_out, 1);
    Serial.print(",");
    Serial.println(sistema_activo ? 1 : 0);

    last_time = now;
  }
}
