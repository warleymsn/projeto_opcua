import time
import sys
import logging
from typing import Optional, Any

# Bibliotecas de Terceiros
from opcua import Client, ua
import paho.mqtt.client as mqtt

# --- CONFIGURAÇÕES E CONSTANTES ---

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("Gateway_IIoT")

class Config:
    """Centraliza as configurações do sistema."""
    # MQTT
    MQTT_BROKER = "131.255.82.115"
    MQTT_PORT = 1883
    MQTT_CLIENT_ID = "UEA-MPEE-sic-gw"
    
    # Tópicos MQTT
    TOPIC_PUB_FLAG = "UEA/MPEE/sic/Flag"           # Publica estado da Flag
    TOPIC_PUB_COUNTER = "UEA/MPEE/sic/gw/Contador" # Publica valor do Contador
    TOPIC_SUB_COUNTER = "UEA/MPEE/sic/Contador"    # Escuta para escrever no OPC
    TOPIC_SUB_REQ_READ = "UEA/MPEE/sic/gw/LerDados" # Escuta requisição de leitura
    
    # OPC UA
    OPC_URL = "opc.tcp://localhost:4840"
    NODE_ID_FLAG = "ns=1;i=1000"      # Nó de Leitura (Boolean)
    NODE_ID_COUNTER = "ns=1;i=1001"   # Nó de Escrita (Int)

class IndustrialGateway:
    """
    Gateway de integração entre protocolo MQTT e servidor OPC UA.
    Gerencia conexões, tradução de mensagens e monitoramento de estados.
    """

    def __init__(self):
        # Estado dos Clientes
        self.mqtt_client: Optional[mqtt.Client] = None
        self.opc_client: Optional[Client] = None
        
        # Estado dos Nós OPC UA
        self.node_flag: Optional[ua.Node] = None
        self.node_counter: Optional[ua.Node] = None
        
        # Controle de Execução
        self._running = True

    def _setup_mqtt(self):
        """Configura e conecta o cliente MQTT."""
        # Nota: Mantendo CallbackAPIVersion.VERSION1 conforme código original
        self.mqtt_client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1, 
            client_id=Config.MQTT_CLIENT_ID
        )
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        
        logger.info(f"[MQTT] Conectando ao Broker {Config.MQTT_BROKER}...")
        try:
            self.mqtt_client.connect(Config.MQTT_BROKER, Config.MQTT_PORT, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            logger.critical(f"[MQTT] Falha fatal na conexão: {e}")
            sys.exit(1)

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback de conexão MQTT."""
        if rc == 0:
            logger.info("[MQTT] Conectado com sucesso!")
            client.subscribe(Config.TOPIC_SUB_COUNTER)
            client.subscribe(Config.TOPIC_SUB_REQ_READ)
            logger.info(f"[MQTT] Inscrito em: {Config.TOPIC_SUB_COUNTER}")
            logger.info(f"[MQTT] Inscrito em: {Config.TOPIC_SUB_REQ_READ}")
        else:
            logger.error(f"[MQTT] Falha na conexão. Código de retorno: {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        """
        Callback de recebimento de mensagem MQTT.
        Gerencia escrita no OPC UA ou requisição de leitura forçada.
        """
        topic = msg.topic
        
        # 1. Escrita no Contador (MQTT -> OPC UA)
        if topic == Config.TOPIC_SUB_COUNTER:
            try:
                valor_str = msg.payload.decode()
                valor_int = int(valor_str)
                logger.info(f"[Gateway] Comando recebido p/ Contador: {valor_int}")

                if self.node_counter:
                    dv = ua.DataValue(ua.Variant(valor_int, ua.VariantType.Int32))
                    self.node_counter.set_value(dv)
                    logger.info(f"[OPC-UA] Escrito {valor_int} no nó Contador.")
                else:
                    logger.error("[Erro] Nó OPC Contador não inicializado.")

            except Exception as e:
                logger.error(f"[Erro Escrita] Falha ao processar mensagem: {e}")

        # 2. Requisição de Leitura (OPC UA -> MQTT)
        elif topic == Config.TOPIC_SUB_REQ_READ:
            logger.info("[Gateway] Requisição de leitura recebida. Lendo OPC-UA...")
            
            if self.node_counter and self.node_flag:
                try:
                    val_flag = self.node_flag.get_value()
                    val_cont = self.node_counter.get_value()

                    # Publica snapshot dos dados
                    client.publish(Config.TOPIC_PUB_COUNTER, str(val_cont))
                    
                    # Mantido time.sleep(3) conforme funcionalidade original
                    # OBS: Em produção, evitar sleeps dentro de callbacks MQTT
                    time.sleep(3) 
                    
                    client.publish(Config.TOPIC_PUB_FLAG, str(val_flag))
                    logger.info(f"[Gateway] Dados Atualizados Enviados: Flag={val_flag}, Cont={val_cont}")

                except Exception as e:
                    logger.error(f"[Erro Leitura] Falha ao ler nós OPC: {e}")
            else:
                logger.warning("[Erro] Nós OPC não prontos para leitura.")

    def run(self):
        """Loop principal de execução e reconexão do Gateway."""
        self._setup_mqtt()
        
        logger.info("--- Iniciando Gateway MQTT <-> OPC-UA ---")
        logger.info("Pressione Ctrl+C para encerrar.")

        while self._running:
            logger.info(f"[OPC-UA] Tentando conectar a {Config.OPC_URL}...")
            
            try:
                self.opc_client = Client(Config.OPC_URL)
                
                with self.opc_client:
                    logger.info(f"[OPC-UA] Conectado ao servidor.")
                    
                    # Inicialização dos Nós
                    try:
                        self.node_flag = self.opc_client.get_node(Config.NODE_ID_FLAG)
                        self.node_counter = self.opc_client.get_node(Config.NODE_ID_COUNTER)
                    except Exception as e:
                        logger.error(f"[OPC-UA] Erro ao obter nós: {e}")
                        raise e

                    # Variáveis de controle de fluxo
                    last_flag_value = False
                    is_first_update = True
                    
                    logger.info("[Gateway] Ciclo de monitoramento iniciado...")

                    # Loop de Polling (Monitoramento Passivo)
                    while self._running:
                        try:
                            current_flag = self.node_flag.get_value()

                            # Lógica: Publicar apenas na mudança de estado (Report by Exception)
                            # Ou se for a primeira execução do loop
                            if not is_first_update and current_flag == last_flag_value:
                                time.sleep(1)
                                continue

                            # Atualiza estado e publica
                            last_flag_value = current_flag
                            is_first_update = False

                            self.mqtt_client.publish(Config.TOPIC_PUB_FLAG, str(current_flag))
                            
                            # Publicação opcional do contador síncrona à mudança da flag
                            current_counter = self.node_counter.get_value()
                            self.mqtt_client.publish(Config.TOPIC_PUB_COUNTER, str(current_counter))

                            logger.info(f"[Gateway] Mudança (Flag): {current_flag} -> Publicado.")
                            time.sleep(1)

                        except Exception as e:
                            logger.error(f"[Erro no Loop OPC] {e}")
                            time.sleep(2)
                            break # Quebra loop interno para forçar reconexão OPC

            except KeyboardInterrupt:
                logger.info("\n[Sistema] Solicitação de encerramento (Ctrl+C)...")
                self._running = False
                
            except Exception as e:
                logger.error(f"[Erro Conexão OPC] {e}")
                logger.info("[OPC-UA] Tentando reconectar em 2s...")
                time.sleep(2)
        
        self._cleanup()

    def _cleanup(self):
        """Encerramento gracioso dos recursos."""
        logger.info("[Sistema] Finalizando processos...")
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        logger.info("[Sistema] Gateway encerrado.")

if __name__ == "__main__":
    gateway = IndustrialGateway()
    gateway.run()