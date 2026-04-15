import json
import socket
import threading
import os
import uvicorn
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

load_dotenv()

# --------------- Configuracao via variaveis de ambiente ---------------
NODE_NAME = os.environ.get("NODE_NAME", "No_A")
UDP_PORT = int(os.environ.get("UDP_PORT", "5000"))
HTTP_PORT = int(os.environ.get("HTTP_PORT", "8000"))

NEIGHBORS: dict[str, dict] = {}
for _i in [1, 2]:
    _name = os.environ.get(f"NEIGHBOR_{_i}_NAME")
    _ip = os.environ.get(f"NEIGHBOR_{_i}_IP")
    _port = os.environ.get(f"NEIGHBOR_{_i}_PORT")
    if _name and _ip and _port:
        NEIGHBORS[_name] = {"name": _name, "ip": _ip, "port": int(_port)}

# --------------- Estado global (protegido por lock) ---------------
lock = threading.Lock()
conversations: dict[str, list[dict]] = {name: [] for name in NEIGHBORS}
msg_counter = 0

# --------------- Socket UDP (SOCK_DGRAM) ---------------
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.bind(("0.0.0.0", UDP_PORT))


def get_local_ip() -> str:
    """Descobre o IP local da interface de saida."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


LOCAL_IP = get_local_ip()


# --------------- Thread de escuta UDP ---------------
def udp_listener():
    """Recebe pacotes UDP em loop e armazena nas conversas."""
    global msg_counter
    while True:
        data, addr = udp_sock.recvfrom(65535)
        try:
            msg = json.loads(data.decode("utf-8"))
            # A conversa eh identificada pelo remetente do pacote
            conv_name = msg["sender_name"]
            with lock:
                if conv_name in conversations:
                    msg_counter += 1
                    msg["id"] = msg_counter
                    conversations[conv_name].append(msg)
        except Exception as e:
            print(f"[UDP] Erro ao processar pacote: {e}")


threading.Thread(target=udp_listener, daemon=True).start()

# --------------- FastAPI ---------------
app = FastAPI(title="Chat P2P UDP")


@app.get("/api/config")
def get_config():
    """Retorna configuracao do no atual e seus vizinhos."""
    return {
        "node_name": NODE_NAME,
        "ip": LOCAL_IP,
        "udp_port": UDP_PORT,
        "neighbors": NEIGHBORS,
    }


@app.get("/api/messages/{neighbor_name}")
def get_messages(neighbor_name: str):
    """Retorna todas as mensagens de uma conversa."""
    with lock:
        return list(conversations.get(neighbor_name, []))


@app.get("/api/status")
def get_status():
    """Retorna contagem de mensagens por conversa (para polling eficiente)."""
    with lock:
        return {name: len(msgs) for name, msgs in conversations.items()}


# --- Modelos Pydantic ---
class SendRequest(BaseModel):
    dest_name: str
    content: str


class ForwardRequest(BaseModel):
    msg_id: int
    dest_name: str


@app.post("/api/send")
def send_message(req: SendRequest):
    """Envia mensagem original para um vizinho via UDP."""
    global msg_counter
    if req.dest_name not in NEIGHBORS:
        return {"error": "Vizinho desconhecido"}

    neighbor = NEIGHBORS[req.dest_name]

    # Estrutura da mensagem conforme especificacao
    msg = {
        "timestamp": datetime.now().isoformat(),
        "sender_name": NODE_NAME,
        "sender_ip": LOCAL_IP,
        "sender_port": UDP_PORT,
        "dest_name": req.dest_name,
        "dest_ip": neighbor["ip"],
        "dest_port": neighbor["port"],
        "content": req.content,
        "forwarded": False,
        "forwarded_by_name": None,
        "original_sender_name": None,
    }

    # Envia via socket UDP (SOCK_DGRAM)
    udp_sock.sendto(
        json.dumps(msg).encode("utf-8"),
        (neighbor["ip"], neighbor["port"]),
    )

    # Armazena localmente na conversa
    with lock:
        msg_counter += 1
        msg["id"] = msg_counter
        msg["is_mine"] = True
        conversations[req.dest_name].append(msg)

    return {"ok": True}


@app.post("/api/forward")
def forward_message(req: ForwardRequest):
    """Encaminha uma mensagem recebida para outro vizinho."""
    global msg_counter

    # Busca a mensagem original
    with lock:
        original = None
        for conv_msgs in conversations.values():
            for m in conv_msgs:
                if m.get("id") == req.msg_id:
                    original = m.copy()
                    break
            if original:
                break

    if not original:
        return {"error": "Mensagem nao encontrada"}
    if req.dest_name not in NEIGHBORS:
        return {"error": "Vizinho desconhecido"}

    neighbor = NEIGHBORS[req.dest_name]

    # Preserva o remetente original (encadeamento de encaminhamentos)
    original_sender = original.get("original_sender_name") or original["sender_name"]

    msg = {
        "timestamp": datetime.now().isoformat(),
        "sender_name": NODE_NAME,
        "sender_ip": LOCAL_IP,
        "sender_port": UDP_PORT,
        "dest_name": req.dest_name,
        "dest_ip": neighbor["ip"],
        "dest_port": neighbor["port"],
        "content": original["content"],
        "forwarded": True,
        "forwarded_by_name": NODE_NAME,
        "original_sender_name": original_sender,
    }

    udp_sock.sendto(
        json.dumps(msg).encode("utf-8"),
        (neighbor["ip"], neighbor["port"]),
    )

    with lock:
        msg_counter += 1
        msg["id"] = msg_counter
        msg["is_mine"] = True
        conversations[req.dest_name].append(msg)

    return {"ok": True}


# --------------- Servir frontend ---------------
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")


# --------------- Inicializacao ---------------
if __name__ == "__main__":
    print(f"[*] No: {NODE_NAME}")
    print(f"[*] UDP escutando em 0.0.0.0:{UDP_PORT}")
    print(f"[*] HTTP em http://0.0.0.0:{HTTP_PORT}")
    print(f"[*] Vizinhos: {list(NEIGHBORS.keys())}")
    uvicorn.run(app, host="0.0.0.0", port=HTTP_PORT)
