from twilio.twiml.messaging_response import MessagingResponse

def format_whatsapp_response(text: str):
    resp = MessagingResponse()
    resp.message(text)
    return str(resp)