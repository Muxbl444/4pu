// CONFIG_SPEED 1234
// CONFIG_STEPS 1234 4321
// CONFIG_INVERT 0 1
// STATUS
// START
// ABORT
// 
// 
// 


// --- Пины подключения ---
const int DIR_X = 2;
const int STEP_X = 3;
const int DIR_Y = 4;
const int STEP_Y = 5;

const int RELAY_1 = 8;
const int RELAY_2 = 9;
const int RELAY_3 = 10;

const int ENDSTOP_X = A0;
const int ENDSTOP_Y = A1;


// --- Настройки по умолчанию ---
int steps_per_meter_x = 7084;
int steps_per_meter_y = 7084;
unsigned int step_delay_us = 7057;
bool invert_x = false;
bool invert_y = false;

unsigned long lastCommandTime = 0; // Время последней добавленной команды
const unsigned long timeout = 10000; // Таймаут для чего-то в need
bool needMoreRequested = false;



int commandIndex = 0;
bool cutting = false;
bool cuttingStarted = false;
bool paused = false;
bool doneReceived = false;
bool bufferWasFilled = false;
long dx = 0, dy = 0, err = 0;
int sx = 0, sy = 0;





struct Command {
  int index;
  float x, y;
  int delay_ms;  // Для задержек будет храниться значение времени задержки
  bool isDelay;  // Флаг, чтобы понять, является ли команда задержкой
};

// Очередь команд
Command commands[70];
int commandCount = 0;
int currentCommandIndex = 0;
bool isMoving = false;
unsigned long lastMillis = 0;
long currentX = 0, currentY = 0;
long targetX = 0, targetY = 0;
unsigned long delayMillis = 0;
int expectedCommandIndex = 0;  // Индекс следующей ожидаемой команды







void processCommands();
void addCommand(int index, float x, float y, int delay_ms = 0);
void checkAndRequestMoreCommands();
void addCommand();
void handleConfig();
void printStatus();
void startCutting();
void endCutting();
void abortCutting();
void pauseCutting();
void resumeCutting();
void handleConfig();
void setup();
void loop();





void processCommands() {
  if (!cutting || paused) return;  // Прерываем, если не режем или пауза активна

  if (commandCount > 0) {
    Command cmd = commands[0];

    if (cmd.isDelay) {
      if (millis() - lastMillis >= cmd.delay_ms) {
        // Удаляем выполненную delay-команду
        for (int i = 1; i < commandCount; i++) {
          commands[i - 1] = commands[i];
        }
        commandCount--;
        lastMillis = millis();
      }
    } else {
      // Если это команда на движение
      if (!isMoving) {
        targetX = cmd.x;
        targetY = cmd.y;

        dx = abs(targetX - currentX);
        dy = abs(targetY - currentY);
        sx = (currentX < targetX) ? 1 : -1;
        sy = (currentY < targetY) ? 1 : -1;
        err = dx - dy;

        isMoving = true;
      }

      if (isMoving) {
        long e2 = 2 * err;

        if (e2 > -dy) {
          err -= dy;
          if (currentX != targetX) {
            digitalWrite(DIR_X, (sx > 0) ^ invert_x ? HIGH : LOW);
            digitalWrite(STEP_X, HIGH);
            delayMicroseconds(step_delay_us);
            digitalWrite(STEP_X, LOW);
            currentX += sx;
          }
        }

        if (e2 < dx) {
          err += dx;
          if (currentY != targetY) {
            digitalWrite(DIR_Y, (sy > 0) ^ invert_y ? HIGH : LOW);
            digitalWrite(STEP_Y, HIGH);
            delayMicroseconds(step_delay_us);
            digitalWrite(STEP_Y, LOW);
            currentY += sy;
          }
        }

        // Завершили движение — удаляем команду
        if (currentX == targetX && currentY == targetY) {
          isMoving = false;
          for (int i = 1; i < commandCount; i++) {
            commands[i - 1] = commands[i];
          }
          commandCount--;
          lastMillis = millis();
        }
      }
    }
  }

  // Завершение по DONE
  if (doneReceived && commandCount == 0) {
    endCutting();
  }
}



void addCommand(int index, float x, float y, int delay_ms = 0) {
  if (!cuttingStarted) return;


  // Если команда уже была принята ранее — подтверждаем повторно
  for (int i = 0; i < commandCount; i++) {
    if (commands[i].index == index) {
      Serial.print("OKE ");
      Serial.println(index);
      return;
    }
  }
  if (index != expectedCommandIndex) return;  // Принимаем только команду с ожидаемым индексом
  
  if (commandCount < 70) {
    commands[commandCount].index = index;
    commands[commandCount].delay_ms = delay_ms;
    commands[commandCount].isDelay = (delay_ms > 0);
    commands[commandCount].x = x * steps_per_meter_x / 1000.0;
    commands[commandCount].y = y * steps_per_meter_y / 1000.0;
    
    Serial.print("OKE ");
    Serial.println(index);
  
     
    

    commandCount++;
    expectedCommandIndex++;
    lastCommandTime = millis();
    needMoreRequested = false;  // Сбросим флаг запроса

    // Проверка заполнения буфера на 30 команд
    if (!bufferWasFilled && commandCount >= 1) {
        bufferWasFilled = true;
        Serial.println("BUFFER WORK!");
      }
   
  }
}

void checkAndRequestMoreCommands() {
  if (cuttingStarted && !doneReceived &&
      bufferWasFilled && commandCount < 15 &&
      (millis() - lastCommandTime >= timeout) &&
      !needMoreRequested) {

    Serial.println("NEED MORE");
    needMoreRequested = true;
  }

}


void handleCommand(String command) {

   if (command.startsWith("CONFIG_SPEED")) {
    step_delay_us = command.substring(13).toInt();
    Serial.println("SPEED SET");
    
  }
  else if (command.startsWith("CONFIG_STEPS")) {
    String params = command.substring(13);
    int spaceIndex = params.indexOf(' ');
    if (spaceIndex > 0) {
      steps_per_meter_x = params.substring(0, spaceIndex).toInt();
      steps_per_meter_y = params.substring(spaceIndex + 1).toInt();
      Serial.println("STEPS SET");
    }
  }
  else if (command.startsWith("CONFIG_INVERT")) {
    String params = command.substring(14);
    int spaceIndex = params.indexOf(' ');
    if (spaceIndex > 0) {
      invert_x = params.substring(0, spaceIndex).toInt();
      invert_y = params.substring(spaceIndex + 1).toInt();
      Serial.println("INVERT SET");
    }
  }
  else if (command == "START") {
    startCutting();
  }
  else if (command == "DONE") {
    doneReceived = true;
  }
  else if (command == "PAUSE") {
    pauseCutting();
  }
  else if (command == "RESUME") {
    resumeCutting();
  }
  else if (command == "ABORT") {
    abortCutting();
  }
  else if (command == "STATUS") {
    printStatus();
  }
  else if (cuttingStarted) {
    int space1 = command.indexOf(' ');
    if (space1 == -1) return;

    int index = command.substring(0, space1).toInt();
    String rest = command.substring(space1 + 1);
    int space2 = rest.indexOf(' ');

    // Задержка: если одно число без точки
    if (space2 == -1 && rest.indexOf('.') == -1) {
      int delayValue = rest.toInt();
      addCommand(index, 0, 0, delayValue);
    } 
    // Движение: два значения с точками
    else if (space2 != -1) {
      String xStr = rest.substring(0, space2);
      String yStr = rest.substring(space2 + 1);

      if (xStr.indexOf('.') != -1 && yStr.indexOf('.') != -1) {
        float x = xStr.toFloat();
        float y = yStr.toFloat();
        addCommand(index, x, y);
      }
    }
  }
}

void printStatus() {
  Serial.println("--- STATUS ---");
  Serial.print("Cutting: "); Serial.println(cutting ? "YES" : "NO");
  Serial.print("Paused: "); Serial.println(paused ? "YES" : "NO");

  Serial.print("Relay 1 (Motors): "); Serial.println(digitalRead(RELAY_1) == LOW ? "ON" : "OFF");
  Serial.print("Relay 2 (Water On): "); Serial.println(digitalRead(RELAY_2) == LOW ? "ON" : "OFF");
  Serial.print("Relay 3 (Water Off): "); Serial.println(digitalRead(RELAY_3) == LOW ? "ON" : "OFF");

  Serial.print("Endstop X: "); Serial.println(digitalRead(ENDSTOP_X) == LOW ? "TRIGGERED" : "OK");
  Serial.print("Endstop Y: "); Serial.println(digitalRead(ENDSTOP_Y) == LOW ? "TRIGGERED" : "OK");

  Serial.print("Step Delay (Speed): "); Serial.println(step_delay_us);
  Serial.print("Steps per Meter X: "); Serial.println(steps_per_meter_x);
  Serial.print("Steps per Meter Y: "); Serial.println(steps_per_meter_y);

  Serial.print("Invert X: "); Serial.println(invert_x ? "YES" : "NO");
  Serial.print("Invert Y: "); Serial.println(invert_y ? "YES" : "NO");
  Serial.println("---------------");
}
void startCutting() {
  currentCommandIndex = 0;
  commandCount = 0;
  doneReceived = false;
  expectedCommandIndex = 0;

  digitalWrite(RELAY_1, LOW);  // удержание моторов (включаем моторы)
  delay(500);                  // задержка на 500 мс
  digitalWrite(RELAY_2, LOW);  // разгон струны (включаем реле 2)
  delay(5000);                 // задержка на 5 секунд для разгона
  digitalWrite(RELAY_2, HIGH); // включаем струну
  cutting = true;              // начинаем резку
  paused = false;              // не в паузе
  cuttingStarted = true;
  Serial.println("CUTTING STARTED");
}
void endCutting() {
  digitalWrite(RELAY_3, LOW);
  delay(1000);
  digitalWrite(RELAY_3, HIGH);
  digitalWrite(RELAY_1, HIGH);
  cutting = false;
  paused = false;
  doneReceived = false;
  cuttingStarted = false;
  currentCommandIndex = commandCount;  // Очищаем очередь
  bufferWasFilled = false;
  Serial.println("CUTTING ENDED");
}
void abortCutting() {
  
  cutting = false;
  doneReceived = false;
  paused = false;
  cuttingStarted = false;
  currentCommandIndex = commandCount;  // Очищаем очередь
  bufferWasFilled = false;
  digitalWrite(RELAY_3, LOW);
  delay(1000);
  digitalWrite(RELAY_3, HIGH);
  digitalWrite(RELAY_1, HIGH);
  Serial.println("ABORTED");
}
void pauseCutting() {
  if (isMoving) {
    // Если двигатели еще двигаются, то подождем их завершения
    return;
  }
  digitalWrite(RELAY_3, LOW);
  delay(1000);
  digitalWrite(RELAY_3, HIGH);
  paused = true;
  Serial.println("PAUSED");
}
void resumeCutting() {
  digitalWrite(RELAY_2, LOW);
  delay(5000);
  digitalWrite(RELAY_2, HIGH);
  paused = false;
  Serial.println("RESUMED");
}
void setup() {
  Serial.begin(115200);
  while (!Serial) {} 

  pinMode(DIR_X, OUTPUT);
  pinMode(STEP_X, OUTPUT);
  pinMode(DIR_Y, OUTPUT);
  pinMode(STEP_Y, OUTPUT);

  pinMode(RELAY_1, OUTPUT);
  pinMode(RELAY_2, OUTPUT);
  pinMode(RELAY_3, OUTPUT);

  pinMode(ENDSTOP_X, INPUT_PULLUP);
  pinMode(ENDSTOP_Y, INPUT_PULLUP);

  digitalWrite(RELAY_1, HIGH);
  digitalWrite(RELAY_2, HIGH);
  digitalWrite(RELAY_3, HIGH);



  Serial.println("READY");
}


void loop() {
  static String inputBuffer;
  // Чтение команды из последовательного порта
  while (Serial.available()) {
    char c = Serial.read();
    
    // Когда получаем символ новой строки или возврата каретки
    if (c == '\n' || c == '\r') {
      if (inputBuffer.length() > 0) {
        inputBuffer.trim();
        inputBuffer.toUpperCase();
        handleCommand(inputBuffer); // Обработка команды
        inputBuffer = "";  // Очистка буфера после обработки
      }
    } else {
      inputBuffer += c;  // Добавляем символ в буфер
    }
  }


  processCommands();  // Обрабатываем команду (движение/задержка)
   
  // Дополнительные операции, которые не блокируют порт
  checkAndRequestMoreCommands();

  // Проверка состояния концевиков при активной резке
  if ((digitalRead(ENDSTOP_X) == LOW || digitalRead(ENDSTOP_Y) == LOW) && cutting) {
    abortCutting();
    Serial.println("ENDSTOP ALARM");
  }
}


