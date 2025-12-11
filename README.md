# 🏭 Miniprojeto IIoT: Gateway ESP32 MQTT ↔ OPC UA

![Status](https://img.shields.io/badge/Status-Concluído-success)
![Linguagem](https://img.shields.io/badge/Python-3.9+-blue)
![Hardware](https://img.shields.io/badge/ESP32-DevKitV1-lightgrey)
![Protocolos](https://img.shields.io/badge/Protocolos-MQTT%20%7C%20OPC%20UA-orange)

Este repositório contém a implementação de um sistema de interoperabilidade para Indústria 4.0, conectando um dispositivo de borda (**ESP32**) a um nível de supervisão (**OPC UA**) através de um Gateway proprietário desenvolvido em Python.

Desenvolvido como requisito da disciplina **Sistemas Inteligentes e Conectados** do **PPGEEL (Programa de Pós-graduação em Engenharia Elétrica)** da UEA - Turma 2025.

---

## 👥 Autores
* **Warley Nogueira**
* **João Neves**

---

## 🎯 Objetivo e Funcionalidades

O projeto resolve o problema de comunicação entre protocolos distintos (OT/IT), atuando como uma ponte bidirecional:

### 1. Monitoramento (Sentido Ascendente)
* **Origem:** O ESP32 gera um contador numérico (`Int16`).
* **Transporte:** Publica via MQTT no tópico `UEA/MPEE/sic/Contador`.
* **Destino:** O Gateway recebe e escreve no Servidor OPC UA (Nó `ns=1;i=1001`).

### 2. Controle (Sentido Descendente)
* **Origem:** O Servidor OPC UA possui uma `Flag` de controle (Booleana) no nó `ns=1;i=1000`.
* **Transporte:** O Gateway monitora este nó e, ao detectar mudança, publica no MQTT (`UEA/MPEE/sic/Flag`).
* **Ação:** O ESP32 reage ao comando:
    * ✅ **Flag = True:** O contador oscila em onda triangular (**0 → 9 → 0**).
    * ⏸️ **Flag = False:** O contador pausa no valor atual.

---

## 🏗️ Arquitetura do Sistema

O sistema é organizado em camadas de rede, mensageria e aplicação:

```mermaid
graph LR
    subgraph "Nível de Campo (Planta)"
        ESP32[("ESP32<br/>(Cliente MQTT)")]
        style ESP32 fill:#d5e8d4,stroke:#82b366
    end

    subgraph "Middleware de Integração"
        Broker[("Broker MQTT<br/>(Porta 1883)")]
        style Broker fill:#dae8fc,stroke:#6c8ebf
        GW["Gateway Python<br/>(Translator)"]
        style GW fill:#fff2cc,stroke:#d6b656
    end

    subgraph "Nível de Supervisão"
        OPC_Server[("Servidor OPC UA<br/>(Porta 4840)")]
        style OPC_Server fill:#f8cecc,stroke:#b85450
    end

    ESP32 -->|"Pub: Contador"| Broker
    Broker -->|"Sub: Contador"| GW
    GW -->|"Write: ns=1;i=1001"| OPC_Server

```
