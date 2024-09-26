import fitz
import re
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import google.generativeai as genai
import os 
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações de API do Google Gemini
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

# Configurações do Twilio
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_client = Client(account_sid, auth_token)

# Configurações do modelo Gemini
generation_config = {
    "temperature": 0.5,
    "top_p": 0.95,
    "top_k": 35,
    "candidate_count": 1,
}
safety_settings = {
    "HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE",
    "HATE": "BLOCK_MEDIUM_AND_ABOVE",
    "SEXUAL": "BLOCK_MEDIUM_AND_ABOVE",
    "DANGEROUS": "BLOCK_MEDIUM_AND_ABOVE",
}

modelo = genai.GenerativeModel(model_name="gemini-1.0-pro",
                              generation_config=generation_config,
                              safety_settings=safety_settings)

# Função para extrair texto de um PDF
def extrair_texto_pdf(caminho_pdf):
    with fitz.open(caminho_pdf) as doc:
        texto = ""
        for pagina in doc:
            texto += pagina.get_text()
    return texto

# Função para pré-processar o texto
def pre_processar_texto(texto):
    texto = texto.lower()
    texto = re.sub(r"[^\w\s]", "", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto

# Função para gerar respostas usando o modelo Gemini
def gerar_resposta(pergunta, contexto):
    prompt = f"{contexto}\n\nPergunta: {pergunta}"
    resposta = modelo.generate_content(prompt)
    return resposta.text

# Configurar o servidor Flask
app = Flask(__name__)

# Carregar o texto do PDF uma vez ao iniciar o servidor
caminho_pdf = "manual.pdf"
texto_pdf = extrair_texto_pdf(caminho_pdf)
texto_pre_processado = pre_processar_texto(texto_pdf)
contexto = texto_pre_processado

# Dicionário para armazenar estados de interação dos usuários
interacao_usuario = {}

# Rota para receber mensagens do Twilio
@app.route("/webhook", methods=["POST"])
def webhook_whatsapp():
    global contexto
    # Obter a mensagem recebida do usuário
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From')  # Número do usuário que enviou a mensagem

    # Verificar se é a primeira interação do usuário
    if from_number not in interacao_usuario:
        interacao_usuario[from_number] = True  # Marcar o usuário como tendo interagido
        mensagem_bem_vinda = "Olá! Bem-vindo ao Botcha! Posso te ajudá-lo com qualquer dúvidas sobre a empresa EuroFarma. Como posso te ajudar hoje?"
        
        # Criar uma resposta de boas-vindas
        resp = MessagingResponse()
        msg = resp.message()
        msg.body(mensagem_bem_vinda)
        return str(resp)

    # Gerar a resposta com base na pergunta do usuário
    resposta = gerar_resposta(incoming_msg, contexto)

    # Atualizar o contexto
    contexto += f"\n\nPergunta: {incoming_msg}\nResposta: {resposta}"

    # Criar uma resposta automática para o usuário via Twilio
    resp = MessagingResponse()
    msg = resp.message()
    msg.body(resposta)

    return str(resp)

if __name__ == "__main__":
    app.run(port=5000)
