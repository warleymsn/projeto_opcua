import time
from opcua import ua, Server

# Configurações do servidor
ENDPOINT = "opc.tcp://0.0.0.0:4840"   # o cliente pode conectar com opc.tcp://localhost:4840
NAMESPACE_URI = "urn:example:opcua:flag-counter"

def main():
    server = Server()
    try:
        # Endpoint e namespace
        server.set_endpoint(ENDPOINT)
        idx = server.register_namespace(NAMESPACE_URI)

        # Raiz dos objetos
        objects = server.get_objects_node()

        # Objeto de demonstração
        demo = objects.add_object(idx, "Demo")

        # Variáveis: criamos com NodeIds tipo string para "ns=2;s=flag" e "ns=2;s=counter"
        # Obs.: Para fixar ns=2, usamos add_variable com o namespace idx (que deve ser 2).
        # Em muitos casos, o primeiro namespace custom é mesmo 2.
        
        flag_var = demo.add_variable("ns=1;i=1000", "Flag", ua.Variant(False, ua.VariantType.Boolean))
        contador_var = demo.add_variable("ns=1;i=1001", "Contador", ua.Variant(0, ua.VariantType.Int16))

        # Permitir escrita pelo cliente
        flag_var.set_writable()
        contador_var.set_writable()

        # Inicia o servidor
        server.start()
        print(f"Servidor OPC UA iniciado em {ENDPOINT}")
        print("Variáveis expostas:")
        print(f"  - flag    → NodeId=ns=1;i=1000 (Boolean, gravável)")
        print(f"  - contador → NodeId=ns=1;i=1001 (Int16, gravável)")
        print("Pressione Ctrl+C para encerrar.")

        # Loop simples apenas para log periódico (o servidor roda em background)
        while True:
            try:
                f = str(flag_var.get_value())
                c = contador_var.get_value()
                print(f"[LOG] flag={f} | counter={c}")
                time.sleep(0.5)
            except KeyboardInterrupt:
                print("\nEncerrando servidor por KeyboardInterrupt...")
                break
            except Exception as e:
                print(f"Erro no loop do servidor: {e}")
                time.sleep(1.0)
                
    finally:
        server.stop()
        print("Servidor OPC UA parado.")

if __name__ == "__main__":
    main()