import os
import hmac
import hashlib
import requests
from flask import Flask, request

app = Flask(__name__)

# ===== CONFIGURAÇÕES =====
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "transmarques_verificacao")
APP_SECRET = os.getenv("APP_SECRET", "")
GRAPH_VERSION = os.getenv("GRAPH_VERSION", "v23.0")

clientes = {}


def enviar_mensagem(numero, texto):
    """Envia uma mensagem de texto pelo WhatsApp Cloud API."""
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("ERRO: WHATSAPP_TOKEN ou PHONE_NUMBER_ID não configurado.")
        return False

    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto},
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        print("WhatsApp:", response.status_code, response.text)
        return response.ok
    except requests.RequestException as e:
        print("Erro ao enviar mensagem:", e)
        return False


def menu():
    return (
        "🏍️ *TRANSMARQUES*\n\n"
        "Olá! Seja bem-vindo ao atendimento automático.\n\n"
        "Escolha uma opção:\n\n"
        "1️⃣ Pedir uma moto\n"
        "2️⃣ Fazer uma entrega\n"
        "3️⃣ Consultar preços\n"
        "4️⃣ Área de atendimento\n"
        "5️⃣ Falar com atendente\n"
        "6️⃣ Sobre a TRANSMARQUES\n\n"
        "Digite apenas o número da opção."
    )


def processar_mensagem(numero, texto):
    texto = texto.strip()
    chave = numero
    cliente = clientes.setdefault(chave, {"estado": "menu"})

    # Menu inicial
    if texto.lower() in {"oi", "olá", "ola", "menu", "inicio", "início", "0"}:
        cliente.clear()
        cliente["estado"] = "menu"
        enviar_mensagem(numero, menu())
        return

    estado = cliente.get("estado", "menu")

    if estado == "menu":
        if texto == "1":
            cliente["estado"] = "nome"
            enviar_mensagem(numero, "🏍️ Vamos solicitar a sua moto.\n\nQual é o seu nome?")
        elif texto == "2":
            cliente["estado"] = "entrega_nome"
            enviar_mensagem(numero, "📦 Vamos organizar a sua entrega.\n\nQual é o seu nome?")
        elif texto == "3":
            enviar_mensagem(
                numero,
                "💰 *Tabela de preços*\n\n"
                "As tarifas variam conforme distância e local.\n"
                "Envie a origem e o destino para receber uma estimativa.\n\n"
                "Digite *1* para pedir uma moto."
            )
        elif texto == "4":
            enviar_mensagem(
                numero,
                "📍 *Área de atendimento*\n\n"
                "A TRANSMARQUES atende conforme disponibilidade dos nossos moto-taxistas.\n"
                "Envie a sua localização ou indique o bairro para verificarmos o atendimento."
            )
        elif texto == "5":
            enviar_mensagem(
                numero,
                "👨‍💼 *Atendimento humano*\n\n"
                "Um atendente da TRANSMARQUES poderá continuar o seu atendimento.\n"
                "Por favor, envie a sua mensagem e aguarde o contacto."
            )
        elif texto == "6":
            enviar_mensagem(
                numero,
                "🏍️ *TRANSMARQUES*\n\n"
                "Serviço de moto-táxi e entregas com atendimento rápido e prático.\n\n"
                "WhatsApp: +244 929 661 088"
            )
        else:
            enviar_mensagem(numero, "Não entendi. 😅\n\n" + menu())

    elif estado == "nome":
        cliente["nome"] = texto
        cliente["estado"] = "origem"
        enviar_mensagem(numero, f"Prazer, {texto}! 👋\n\n📍 Qual é o local de partida (origem)?")

    elif estado == "origem":
        cliente["origem"] = texto
        cliente["estado"] = "destino"
        enviar_mensagem(numero, "📍 Qual é o local de destino?")

    elif estado == "destino":
        cliente["destino"] = texto
        nome = cliente.get("nome", "")
        origem = cliente.get("origem", "")
        destino = cliente.get("destino", "")

        mensagem = (
            "🏍️ *NOVO PEDIDO — TRANSMARQUES*\n\n"
            f"👤 Nome: {nome}\n"
            f"📍 Origem: {origem}\n"
            f"🏁 Destino: {destino}\n"
            f"📱 Cliente: {numero}\n\n"
            "Responda ao cliente para confirmar o pedido."
        )

        # Mostra o resumo ao cliente.
        enviar_mensagem(
            numero,
            "✅ *Pedido recebido!*\n\n"
            f"👤 Nome: {nome}\n"
            f"📍 Origem: {origem}\n"
            f"🏁 Destino: {destino}\n\n"
            "Aguarde a confirmação de um moto-taxista da TRANSMARQUES. 🏍️"
        )

        # Regista o pedido no log do servidor.
        print("\n" + "=" * 50)
        print(mensagem)
        print("=" * 50 + "\n")

        cliente.clear()
        cliente["estado"] = "menu"

    elif estado == "entrega_nome":
        cliente["nome"] = texto
        cliente["estado"] = "entrega_origem"
        enviar_mensagem(numero, "📍 Indique o local onde a encomenda será recolhida.")

    elif estado == "entrega_origem":
        cliente["origem"] = texto
        cliente["estado"] = "entrega_destino"
        enviar_mensagem(numero, "🏁 Indique o local de entrega da encomenda.")

    elif estado == "entrega_destino":
        cliente["destino"] = texto
        cliente["estado"] = "entrega_descricao"
        enviar_mensagem(numero, "📦 Descreva brevemente a encomenda.")

    elif estado == "entrega_descricao":
        cliente["descricao"] = texto
        enviar_mensagem(
            numero,
            "✅ *Pedido de entrega recebido!*\n\n"
            f"👤 Nome: {cliente.get('nome', '')}\n"
            f"📍 Recolha: {cliente.get('origem', '')}\n"
            f"🏁 Entrega: {cliente.get('destino', '')}\n"
            f"📦 Encomenda: {cliente.get('descricao', '')}\n\n"
            "A TRANSMARQUES irá confirmar a disponibilidade."
        )
        print("NOVA ENTREGA:", cliente, "Cliente:", numero)
        cliente.clear()
        cliente["estado"] = "menu"

    else:
        cliente.clear()
        cliente["estado"] = "menu"
        enviar_mensagem(numero, menu())


@app.route("/", methods=["GET"])
def inicio():
    return "TRANSMARQUES Bot online ✅", 200


@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Token inválido", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    # Validação opcional da assinatura enviada pela Meta.
    if APP_SECRET:
        assinatura = request.headers.get("X-Hub-Signature-256", "")
        esperado = "sha256=" + hmac.new(
            APP_SECRET.encode(),
            request.get_data(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(assinatura, esperado):
            return "Assinatura inválida", 403

    data = request.get_json(silent=True) or {}

    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                for mensagem in value.get("messages", []):
                    if mensagem.get("type") != "text":
                        continue

                    numero = mensagem.get("from")
                    texto = mensagem.get("text", {}).get("body", "")

                    if numero and texto:
                        processar_mensagem(numero, texto)

    except Exception as e:
        print("Erro no webhook:", e)

    return "EVENT_RECEIVED", 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
