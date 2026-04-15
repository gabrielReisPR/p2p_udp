#!/bin/bash
# Inicia os 3 nos na mesma maquina com portas diferentes
# Uso: ./start.sh

trap 'echo "Parando todos os nos..."; kill $PID_A $PID_B $PID_C 2>/dev/null; exit' INT TERM

NODE_NAME=No_A UDP_PORT=5000 HTTP_PORT=8000 \
NEIGHBOR_1_NAME=No_B NEIGHBOR_1_IP=127.0.0.1 NEIGHBOR_1_PORT=5001 \
NEIGHBOR_2_NAME=No_C NEIGHBOR_2_IP=127.0.0.1 NEIGHBOR_2_PORT=5002 \
python3 main.py &
PID_A=$!

NODE_NAME=No_B UDP_PORT=5001 HTTP_PORT=8001 \
NEIGHBOR_1_NAME=No_A NEIGHBOR_1_IP=127.0.0.1 NEIGHBOR_1_PORT=5000 \
NEIGHBOR_2_NAME=No_C NEIGHBOR_2_IP=127.0.0.1 NEIGHBOR_2_PORT=5002 \
python3 main.py &
PID_B=$!

NODE_NAME=No_C UDP_PORT=5002 HTTP_PORT=8002 \
NEIGHBOR_1_NAME=No_A NEIGHBOR_1_IP=127.0.0.1 NEIGHBOR_1_PORT=5000 \
NEIGHBOR_2_NAME=No_B NEIGHBOR_2_IP=127.0.0.1 NEIGHBOR_2_PORT=5001 \
python3 main.py &
PID_C=$!

echo ""
echo "========================================="
echo "  3 nos rodando!"
echo "========================================="
echo "  No_A -> http://<SEU_IP>:8000"
echo "  No_B -> http://<SEU_IP>:8001"
echo "  No_C -> http://<SEU_IP>:8002"
echo "========================================="
echo "  Ctrl+C para parar tudo"
echo "========================================="
echo ""

wait
