let config = null;
let activeNeighbor = null;
let messageCounts = {};
let seenCounts = {};

async function init() {
    const res = await fetch("/api/config");
    config = await res.json();

    document.getElementById("node-title").textContent = config.node_name;
    document.getElementById("node-info").textContent =
        config.ip + ":" + config.udp_port;

    const tabs = document.getElementById("tabs");
    const names = Object.keys(config.neighbors);

    names.forEach(function (name) {
        var btn = document.createElement("button");
        btn.id = "tab-" + name;
        btn.innerHTML =
            escapeHtml(name) +
            ' <span class="badge" id="badge-' +
            name +
            '"></span>';
        btn.onclick = function () {
            switchTo(name);
        };
        tabs.appendChild(btn);
        messageCounts[name] = 0;
        seenCounts[name] = 0;
    });

    if (names.length > 0) {
        switchTo(names[0]);
    }

    document.getElementById("input-area").onsubmit = function (e) {
        e.preventDefault();
        sendMessage();
    };

    // Polling a cada 1 segundo
    setInterval(poll, 1000);
}

function switchTo(name) {
    activeNeighbor = name;
    var buttons = document.querySelectorAll("#tabs button");
    for (var i = 0; i < buttons.length; i++) {
        buttons[i].classList.remove("active");
    }
    document.getElementById("tab-" + name).classList.add("active");
    seenCounts[name] = messageCounts[name] || 0;
    updateBadges();
    loadMessages(name);
    document.getElementById("msg-input").focus();
}

async function loadMessages(name) {
    var res = await fetch("/api/messages/" + encodeURIComponent(name));
    var messages = await res.json();
    render(messages);
}

function render(messages) {
    var el = document.getElementById("messages");
    var wasAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50;

    el.innerHTML = "";

    for (var i = 0; i < messages.length; i++) {
        var msg = messages[i];
        var div = document.createElement("div");
        div.className = "msg " + (msg.is_mine ? "mine" : "theirs");

        var date = new Date(msg.timestamp);
        var time = date.toLocaleTimeString("pt-BR", {
            hour: "2-digit",
            minute: "2-digit",
        });

        var html =
            '<div class="meta">' +
            escapeHtml(msg.sender_name) +
            " &middot; " +
            time +
            "</div>";

        if (msg.forwarded) {
            html +=
                '<div class="fwd-info">Encaminhado por ' +
                escapeHtml(msg.forwarded_by_name) +
                " [Msg original de " +
                escapeHtml(msg.original_sender_name) +
                "]</div>";
        }

        html += '<div class="content">' + escapeHtml(msg.content) + "</div>";

        // Botao de encaminhar em mensagens recebidas
        if (!msg.is_mine) {
            var other = getOtherNeighbor(activeNeighbor);
            if (other) {
                html +=
                    '<div class="actions">' +
                    "<button onclick=\"fwd(" +
                    msg.id +
                    ",'" +
                    other +
                    "')\">" +
                    "Encaminhar para " +
                    escapeHtml(other) +
                    "</button></div>";
            }
        }

        div.innerHTML = html;
        el.appendChild(div);
    }

    if (wasAtBottom) {
        el.scrollTop = el.scrollHeight;
    }
}

function getOtherNeighbor(current) {
    var names = Object.keys(config.neighbors);
    for (var i = 0; i < names.length; i++) {
        if (names[i] !== current) return names[i];
    }
    return null;
}

async function sendMessage() {
    var input = document.getElementById("msg-input");
    var content = input.value.trim();
    if (!content || !activeNeighbor) return;

    input.value = "";
    await fetch("/api/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dest_name: activeNeighbor, content: content }),
    });
    loadMessages(activeNeighbor);
}

async function fwd(msgId, destName) {
    if (!confirm("Encaminhar mensagem para " + destName + "?")) return;
    await fetch("/api/forward", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ msg_id: msgId, dest_name: destName }),
    });
    loadMessages(activeNeighbor);
}

async function poll() {
    try {
        var res = await fetch("/api/status");
        var counts = await res.json();

        var names = Object.keys(counts);
        for (var i = 0; i < names.length; i++) {
            messageCounts[names[i]] = counts[names[i]];
        }

        // Atualiza seen da conversa ativa
        if (activeNeighbor) {
            seenCounts[activeNeighbor] = messageCounts[activeNeighbor] || 0;
        }

        updateBadges();

        if (activeNeighbor) {
            loadMessages(activeNeighbor);
        }
    } catch (e) {
        // Ignora erros de rede no polling
    }
}

function updateBadges() {
    var names = Object.keys(config.neighbors);
    for (var i = 0; i < names.length; i++) {
        var name = names[i];
        var badge = document.getElementById("badge-" + name);
        var newCount = (messageCounts[name] || 0) - (seenCounts[name] || 0);
        if (newCount > 0 && name !== activeNeighbor) {
            badge.textContent = newCount;
            badge.classList.add("visible");
        } else {
            badge.classList.remove("visible");
        }
    }
}

function escapeHtml(text) {
    var d = document.createElement("div");
    d.textContent = text;
    return d.innerHTML;
}

init();
