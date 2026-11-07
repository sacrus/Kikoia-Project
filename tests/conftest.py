import sys

# Testes do Linux (BlueZ via jeepney, uinput via fcntl) nao sao recolhidos no Windows, e vice-versa.
collect_ignore = []
if sys.platform != "linux":
    collect_ignore += ["test_gateway_bluetooth_linux.py", "test_saida_linux.py"]
