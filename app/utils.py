import os
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import qrcode
import base64
import io
from app.config import Config
import time

def generate_qr_code(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def save_signature_on_pdf(pdf_path, signature_data, x, y):
    try:
        # Processar assinatura
        signature_image_data = signature_data.split(',')[1]
        signature_bytes = base64.b64decode(signature_image_data)
        signature_image = Image.open(io.BytesIO(signature_bytes))
        
        # Converter para RGBA e remover fundo branco
        signature_image = signature_image.convert('RGBA')
        datas = signature_image.getdata()
        new_data = []
        for item in datas:
            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        signature_image.putdata(new_data)
        
        # Salvar assinatura temporária
        temp_sig_path = os.path.join(os.path.dirname(pdf_path), f'temp_sig_{int(time.time())}.png')
        signature_image.save(temp_sig_path, 'PNG')
        
        # Processar PDF
        output_path = pdf_path.replace('.pdf', '_signed.pdf')
        
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        # Copiar todas as páginas
        for i in range(len(reader.pages)):
            page = reader.pages[i]
            
            # Adicionar assinatura apenas na última página
            if i == len(reader.pages) - 1:
                # Obter dimensões da página
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)
                
                # Calcular posição real da assinatura
                sig_x = (float(x) / 100.0) * page_width
                sig_y = page_height - ((float(y) / 100.0) * page_height) - signature_image.height
                
                # Criar camada de assinatura
                packet = io.BytesIO()
                can = canvas.Canvas(packet, pagesize=(page_width, page_height))
                can.drawImage(temp_sig_path, sig_x, sig_y, mask='auto')
                can.save()
                packet.seek(0)
                
                # Mesclar assinatura com a página
                sig_pdf = PdfReader(packet)
                page.merge_page(sig_pdf.pages[0])
            
            writer.add_page(page)
        
        # Salvar PDF final
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        
        # Limpar arquivo temporário
        os.remove(temp_sig_path)
        
        return output_path
        
    except Exception as e:
        print(f"Erro ao processar PDF: {str(e)}")
        raise
