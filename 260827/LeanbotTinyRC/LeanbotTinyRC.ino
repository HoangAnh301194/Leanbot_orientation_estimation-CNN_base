#include <Leanbot.h>

#define TINY_RC_VERSION  "Leanbot Tiny RC 260819:080731"

void setup() {
  Leanbot.begin();
  LbDelay(100);
  Serial.println(TINY_RC_VERSION);
}

// Chờ có command từ Serial
bool waitSerialCommand(long timeout) {
  long timeout_target = millis() + timeout;

  while ((long)(millis() - timeout_target) < 0) {
    if (Serial.available() > 0)
      return true;
  }
  return false;
}

// Xử lý command r/60/70
void Leanbot_run(String args) {

  int pos = args.indexOf('/');

  if (pos < 0)
    return;

  int left  = args.substring(0, pos).toInt();
  int right = args.substring(pos + 1).toInt();

  Serial.print("RunLR(");
  Serial.print(left);
  Serial.print(", ");
  Serial.print(right);
  Serial.println(")");

  LbMotion.runLR(left, right);
}

void stopLeanbot(void) {
  Serial.println("Leanbot Stop");
  LbMotion.runLR(0, 0);
}

void loop() {

  // Chờ command trong tối đa 3000 ms
  while (waitSerialCommand(3000)) {

    String message = Serial.readStringUntil('\n');
    message.trim();

    // -------------------------
    // Parse command
    // r/60/70
    // ^^
    // command = r
    // args    = 60/70
    // -------------------------

    int pos1 = message.indexOf('/');

    if (pos1 < 0)
      continue;

    String cmd  = message.substring(0, pos1);
    String args = message.substring(pos1 + 1);


    // -------------------------
    // Execute command
    // -------------------------

    if (cmd == "r") { // run RL
      Leanbot_run(args);
    }
  }

  // Không có command mới trong 3 giây
  stopLeanbot();
}