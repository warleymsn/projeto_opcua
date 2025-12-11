#include <Arduino.h> // Necessário para PlatformIO/VSCode
#include <WiFi.h>
#include <PubSubClient.h>

/* =================================================================
   1. CONFIGURAÇÕES E CONSTANTES
   ================================================================= */
// Habilita logs na Serial. Comente para desativar em produção.
#define DEBUG 1

// Credenciais Wi-Fi
const char* WIFI_SSID     = "LAB_I4.0";
const char* WIFI_PASS     = "L4B0@2025#";

// Configurações MQTT
const char* MQTT_BROKER   = "131.255.82.115";
const int   MQTT_PORT     = 1883;
const char* MQTT_CLIENT_ID = "ESP32-SIC-Client";

// Definição de Tópicos
const char* TOPIC_SUB_FLAG    = "UEA/MPEE/sic/Flag";
const char* TOPIC_PUB_COUNTER = "UEA/MPEE/sic/Contador";

// Intervalos de Tempo (Timers)
const unsigned long INTERVAL_COUNTER_MS = 1000; // Atualização do contador (1s)
const unsigned long INTERVAL_RECONNECT_MS = 5000; // Tentativa de reconexão (5s)

/* =================================================================
   2. ESTRUTURA DE DADOS E ESTADO GLOBAL
   ================================================================= */
struct SystemState {
  bool isRunning;           // Controlado pela Flag remota
  int16_t counter;          // Valor atual do contador
  int8_t direction;         // +1 (sobe) ou -1 (desce)
  int16_t lastPublished;    // Para otimização de tráfego (F4)
};

// Inicialização do Estado
SystemState sysState = { false, 0, 1, -1 };

// Objetos Globais
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Variáveis de Controle de Tempo
unsigned long lastCounterUpdate = 0;
unsigned long lastReconnectAttempt = 0;

/* =================================================================
   3. MACROS AUXILIARES (LOGGING) - CORRIGIDO
   ================================================================= */
#if DEBUG
  #define LOG_PRINT(x) Serial.print(x)
  #define LOG_PRINTLN(x) Serial.println(x)
  // Usa __VA_ARGS__ para passar qualquer qtde de argumentos para printf
  #define LOG_PRINTF(...) Serial.printf(__VA_ARGS__)
#else
  #define LOG_PRINT(x)
  #define LOG_PRINTLN(x)
  #define LOG_PRINTF(...)
#endif

/* =================================================================
   4. FUNÇÕES DE CALLBACK E LÓGICA
   ================================================================= */

/**
 * @brief Processa mensagens recebidas via MQTT.
 * Utiliza manipulação de char array para evitar fragmentação de heap (String).
 */
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Cria um buffer local seguro (+1 para o terminador nulo)
  char msgBuffer[50];
  unsigned int cleanLength = (length < sizeof(msgBuffer) - 1) ? length : (sizeof(msgBuffer) - 1);
  
  memcpy(msgBuffer, payload, cleanLength);
  msgBuffer[cleanLength] = '\0'; // Garante terminação C-String

  // Agora esta linha funcionará corretamente
  LOG_PRINTF("[MQTT RX] Tópico: %s | Payload: %s\n", topic, msgBuffer);

  // Verifica se o tópico é o de Flag
  if (strcmp(topic, TOPIC_SUB_FLAG) == 0) {
    // Comparação Case-Insensitive segura
    if (strcasecmp(msgBuffer, "true") == 0 || 
        strcmp(msgBuffer, "1") == 0 || 
        strcasecmp(msgBuffer, "on") == 0) {
      sysState.isRunning = true;
      LOG_PRINTLN("[SISTEMA] Estado: RODANDO (Flag=True)");
    } else {
      sysState.isRunning = false;
      LOG_PRINTLN("[SISTEMA] Estado: PAUSADO (Flag=False)");
    }
  }
}

/**
 * @brief Gerencia conexão Wi-Fi (Bloqueante no Boot, pois é essencial).
 */
void setupWiFi() {
  LOG_PRINT("\n[WIFI] Conectando a ");
  LOG_PRINTLN(WIFI_SSID);

  WiFi.mode(WIFI_STA); // Garante modo Station
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    LOG_PRINT(".");
  }

  LOG_PRINTLN("\n[WIFI] Conectado!");
  LOG_PRINT("[WIFI] IP: ");
  LOG_PRINTLN(WiFi.localIP());
}

/**
 * @brief Tenta reconectar ao MQTT de forma NÃO-BLOQUEANTE.
 * Permite que o loop continue rodando (sem delay travado).
 * @return true se conectado, false caso contrário.
 */
bool tryReconnectMQTT() {
  if (mqttClient.connected()) return true;

  unsigned long now = millis();
  // Tenta apenas se passou o intervalo definido (5s)
  if (now - lastReconnectAttempt > INTERVAL_RECONNECT_MS) {
    lastReconnectAttempt = now;
    LOG_PRINT("[MQTT] Tentando conexão... ");

    // Tenta conectar
    if (mqttClient.connect(MQTT_CLIENT_ID)) {
      LOG_PRINTLN("SUCESSO!");
      mqttClient.subscribe(TOPIC_SUB_FLAG);
      LOG_PRINTLN("[MQTT] Inscrito no tópico de Flag.");
      return true;
    } else {
      LOG_PRINT("[FALHA] rc=");
      LOG_PRINTLN(mqttClient.state());
      return false;
    }
  }
  return false;
}

/* =================================================================
   5. SETUP E LOOP PRINCIPAL
   ================================================================= */
void setup() {
  #if DEBUG
    Serial.begin(115200);
    delay(500);
  #endif

  setupWiFi();
  
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
}

void loop() {
  // 1. Verificação de Conectividade (Watchdog de Rede)
  if (WiFi.status() != WL_CONNECTED) {
    setupWiFi(); // Se cair Wi-Fi, reconecta (aqui pode ser bloqueante)
  }
  
  if (!mqttClient.connected()) {
    tryReconnectMQTT();
  } else {
    // Processa pacotes de entrada/saída e mantém keep-alive
    mqttClient.loop();
  }

  // 2. Lógica de Negócio (Contador Triangular)
  unsigned long now = millis();

  if (now - lastCounterUpdate >= INTERVAL_COUNTER_MS) {
    lastCounterUpdate = now;

    // Só atualiza se a flag estiver ativa
    if (sysState.isRunning) {
      // Oscilação 0 -> 9 -> 0
      sysState.counter += sysState.direction;

      // Inversão de direção nos limites
      if (sysState.counter >= 9) {
        sysState.counter = 9; // Garante limite
        sysState.direction = -1;
      } else if (sysState.counter <= 0) {
        sysState.counter = 0; // Garante limite
        sysState.direction = 1;
      }
    }

    // 3. Publicação Otimizada (Report by Exception - F4)
    if (sysState.counter != sysState.lastPublished) {
      
      // Conversão segura int -> string
      char payloadBuffer[8];
      snprintf(payloadBuffer, sizeof(payloadBuffer), "%d", sysState.counter);

      if (mqttClient.connected()) {
        mqttClient.publish(TOPIC_PUB_COUNTER, payloadBuffer);
        
        LOG_PRINTF("[TX] Contador enviado: %s\n", payloadBuffer);
        sysState.lastPublished = sysState.counter;
      }
    }
  }
}