# 🏭 Miniprojeto IIoT: Gateway ESP32 MQTT ↔ OPC UA

![Status](https://img.shields.io/badge/Status-Concluído-success)
![Linguagem](https://img.shields.io/badge/Python-3.11+-blue)
![Hardware](https://img.shields.io/badge/ESP32-DevKitV1-lightgrey)
![Protocolos](https://img.shields.io/badge/Protocolos-MQTT%20%7C%20OPC%20UA-orange)

[cite_start]Este repositório contém a implementação de um sistema de interoperabilidade para Indústria 4.0, conectando um dispositivo de borda (**ESP32**) a um nível de supervisão (**OPC UA**) através de um Gateway proprietário desenvolvido em Python[cite: 1, 17].

[cite_start]Desenvolvido como requisito da disciplina **Sistemas Inteligentes e Conectados** do **PPGEEL (Programa de Pós-graduação em Engenharia Elétrica)** da UEA - Turma 2025[cite: 3, 7].

---

## 👥 Autores
* **Warley Nogueira**
* **João Neves**

---

## 🎯 Objetivo e Funcionalidades

[cite_start]O sistema integra o chão de fábrica (Field Level) com o supervisório (Control Level)[cite: 38].

### Lógica de Controle
1.  **Monitoramento (Uplink):** O ESP32 publica um contador inteiro (`Int16`) via MQTT. [cite_start]O Gateway traduz e escreve este valor em um nó do Servidor OPC UA[cite: 14, 31].
2.  **Controle (Downlink):** O Servidor OPC UA possui uma `Flag` (Booleana). [cite_start]O Gateway monitora esta flag e envia comandos para o ESP32[cite: 13, 30].
    * [cite_start]✅ **Flag = True:** O contador oscila em onda triangular: **0 → 9 → 0**[cite: 15].
    * [cite_start]⏸️ **Flag = False:** O contador pausa no valor atual[cite: 16].

### Tecnologias Utilizadas
* [cite_start]**Firmware:** C++ (Arduino Core / PlatformIO) com lógica não-bloqueante (`millis`)[cite: 67].
* [cite_start]**Gateway:** Python com bibliotecas `paho-mqtt` e `opcua`[cite: 107, 109].
* **Infraestrutura:** Broker MQTT (Mosquitto) e Servidor OPC UA (FreeOpcUa).

---

## 🏗️ Arquitetura do Sistema

```mermaid
graph LR
    subgraph "Chão de Fábrica"
        ESP32[("ESP32 (Cliente MQTT)")]
    end

    subgraph "Middleware"
        Broker[("Broker MQTT (:1883)")]
        Gateway["Gateway Python (Translator)"]
    end

    subgraph "Supervisão"
        OPC[("Servidor OPC UA (:4840)")]
    end

    ESP32 -->|"Pub: Contador"| Broker
    Broker -->|"Sub: Contador"| Gateway
    Gateway -->|"Write: NodeId 1001"| OPC

    OPC -.->|"Read: NodeId 1000"| Gateway
    Gateway -.->|"Pub: Flag"| Broker
    Broker -.->|"Sub: Flag"| ESP32
