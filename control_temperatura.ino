const int PIN_SENSOR = A0;   
const int PIN_HEATER = 6;    

const float R_DIVISOR = 10000.0; 
const float NOMINAL_RESISTANCE = 10000.0;
const float NOMINAL_TEMPERATURE = 25.0;
const float B_COEFFICIENT = 3950.0;

float setpoint = 35.0;     
bool sistema_activo = false;

float Kp = 15.0;  
float Ki = 0.5;   
float Kd = 2.0;   

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
  
  float resistencia = R_DIVISOR * ((1023.0 / rawADC) - 1.0);
  
  float steinhart;
  steinhart = resistencia / NOMINAL_RESISTANCE;     
  steinhart = log(steinhart);                         
  steinhart /= B_COEFFICIENT;                         
  steinhart += 1.0 / (NOMINAL_TEMPERATURE + 273.15); 
  steinhart = 1.0 / steinhart;                        
  steinhart -= 273.15;                              
  
  return steinhart;
}

void loop() {
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();
    
    if (comando.startsWith("START")) {
      sistema_activo = true;
      integral = 0.0; 
    } else if (comando.startsWith("STOP")) {
      sistema_activo = false;
      analogWrite(PIN_HEATER, 0);
    } else if (comando.startsWith("SET:")) {
      setpoint = comando.substring(4).toFloat();
    }
  }

  unsigned long now = millis();
  float dt = (now - last_time) / 1000.0;

  if (dt >= 0.1) {
    float temp_actual = leerTemperatura();
    float pwm_out = 0.0;

    if (sistema_activo) {
      float error = setpoint - temp_actual;
      integral += error * dt;
      
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
