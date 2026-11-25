#!/usr/bin/env bash
# Permite ao utilizador com sessao grafica ativa criar o teclado virtual (/dev/uinput).
# Executar uma vez, com sudo:  sudo tools/configurar_teclado_linux.sh
# Nao junta o utilizador a nenhum grupo: o acesso e dado so a sessao grafica ativa.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Execute com sudo: sudo $0" >&2
    exit 1
fi

REGRA=/etc/udev/rules.d/71-teclado-remoto-uinput.rules
CARREGAR=/etc/modules-load.d/teclado-remoto-uinput.conf

cat > "$REGRA" <<'EOF'
KERNEL=="uinput", SUBSYSTEM=="misc", OPTIONS+="static_node=uinput", TAG+="uaccess"
EOF

echo uinput > "$CARREGAR"
modprobe uinput
udevadm control --reload-rules
udevadm trigger --name-match=uinput

ls -l /dev/uinput
echo "Configurado. Se o teclado ainda nao escrever, termine a sessao e volte a entrar."
