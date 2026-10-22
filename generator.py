import os
import math
import xml.etree.ElementTree as ET
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

FONTES = {"Arial": "Helvetica", "Arial-Bold": "Helvetica-Bold"}
ASCENT, CENTRO = 0.905, 0.3465

POSICOES_FOTOS = [
    (91.0, 123.0),   # Linha 1, Col 1
    (315.7, 123.0),  # Linha 1, Col 2
    (91.0, 330.5),   # Linha 2, Col 1
    (315.7, 330.5),  # Linha 2, Col 2
    (91.0, 538.0),   # Linha 3, Col 1
    (315.7, 538.0),  # Linha 3, Col 2
]

def calcular_km(estaca_val, km_base=198.8, metros_estaca=20.0):
    """Calcula o KM formatado a partir da estaca e parâmetros."""
    try:
        if str(estaca_val).strip() == "":
            return ""
        estaca = float(str(estaca_val).replace(",", "."))
        km = (estaca * float(metros_estaca) / 1000.0) + float(km_base)
        return f"{km:.2f}".replace(".", ",")
    except Exception:
        return ""

def desenhar_cabecalho(c, W, H, campos, logo_path, pagina_num=None, total_paginas=None):
    """Desenha a moldura institucional, logomarca e campos do cabeçalho."""
    # Moldura externa principal
    c.setLineWidth(1.2)
    c.setStrokeColorRGB(0, 0, 0)
    c.rect(71.3, H - 51.5 - 689.6, 479.4, 689.6, stroke=1, fill=0)
    
    # Linha divisória do cabeçalho
    c.line(71.3, H - 112.7, 550.7, H - 112.7)

    # Logomarca DNIT ou personalizada
    if logo_path and os.path.isfile(logo_path):
        try:
            c.drawImage(logo_path, 272.4, H - 22.6 - 21.7, 109.1, 21.7, mask="auto")
        except Exception:
            pass

    # Textos do cabeçalho (Centralizados)
    c.setFont(FONTES["Arial-Bold"], 6.7)
    c.setFillColorRGB(0, 0, 0)
    
    base_y_orgao = H - (53.3 + ASCENT * 6.7)
    c.drawCentredString(311.0, base_y_orgao, campos.get("orgao", ""))
    
    base_y_reg = H - (63.5 + ASCENT * 6.7)
    c.drawCentredString(311.0, base_y_reg, campos.get("regional", ""))
    
    base_y_tit = H - (73.7 + ASCENT * 6.7)
    c.drawCentredString(311.0, base_y_tit, campos.get("titulo", ""))

    # Linha 1 de metadados: Empresa, Contrato, Medição
    # EMPRESA:
    c.setFont(FONTES["Arial-Bold"], 5.5)
    c.drawString(132.5, H - (95.0 + ASCENT * 5.5), "EMPRESA:")
    c.setFont(FONTES["Arial"], 6.1)
    c.drawString(164.1, H - (94.8 + ASCENT * 6.1), str(campos.get("empresa", "")))

    # CONTRATO:
    c.setFont(FONTES["Arial-Bold"], 5.5)
    c.drawString(353.1, H - (95.0 + ASCENT * 5.5), "CONTRATO:")
    c.setFont(FONTES["Arial"], 6.1)
    c.drawString(388.8, H - (94.8 + ASCENT * 6.1), str(campos.get("contrato", "")))

    # MEDIÇÃO:
    c.setFont(FONTES["Arial-Bold"], 5.5)
    c.drawString(502.2, H - (95.0 + ASCENT * 5.5), "MEDIÇÃO:")
    c.setFont(FONTES["Arial"], 6.1)
    c.drawString(532.3, H - (94.8 + ASCENT * 6.1), str(campos.get("medicao", "")))

    # Linha 2 de metadados: Serviços até, Período
    # SERVIÇOS EXECUTADOS ATÉ:
    c.setFont(FONTES["Arial-Bold"], 5.5)
    c.drawString(114.6, H - (105.2 + ASCENT * 5.5), "SERVIÇOS EXECUTADOS ATÉ:")
    c.setFont(FONTES["Arial"], 6.1)
    c.drawString(199.9, H - (105.0 + ASCENT * 6.1), str(campos.get("servicos_ate", "")))

    # PERÍODO: ... a ...
    c.setFont(FONTES["Arial-Bold"], 5.5)
    c.drawString(358.8, H - (105.2 + ASCENT * 5.5), "PERÍODO:")
    c.setFont(FONTES["Arial"], 6.1)
    c.drawString(390.7, H - (105.0 + ASCENT * 6.1), str(campos.get("periodo_inicio", "")))
    c.drawString(440.0, H - (105.0 + ASCENT * 6.1), "a")
    c.drawString(462.5, H - (105.0 + ASCENT * 6.1), str(campos.get("periodo_fim", "")))

    # Paginação discreta no cabeçalho ou rodapé (se multi-página)
    if pagina_num is not None and total_paginas is not None and total_paginas > 1:
        c.setFont(FONTES["Arial"], 6.0)
        c.drawRightString(550.0, H - 40.0, f"Folha {pagina_num}/{total_paginas}")

from PIL import Image
from reportlab.lib.utils import ImageReader

def desenhar_bloco_foto(c, H, ox, oy, foto, rodovia):
    """Desenha um bloco individual de foto (imagem + linhas + células de legenda)."""
    # Imagem
    arq_foto = foto.get("arquivo", "")
    rotacao = foto.get("rotacao", 0)
    if arq_foto and os.path.isfile(arq_foto):
        try:
            if rotacao != 0:
                pil_img = Image.open(arq_foto)
                # PIL gira no sentido anti-horário com valores positivos; convertemos:
                pil_img = pil_img.rotate(-rotacao, expand=True)
                reader = ImageReader(pil_img)
                c.drawImage(reader, ox + 0.1, H - (oy + 0) - 158.6, 214.0, 158.6, mask="auto")
            else:
                c.drawImage(arq_foto, ox + 0.1, H - (oy + 0) - 158.6, 214.0, 158.6, mask="auto")
        except Exception:
            pass
    
    # Contorno e linhas divisórias
    c.setLineWidth(0.6)
    c.setStrokeColorRGB(0, 0, 0)
    c.rect(ox + 0, H - (oy + 0) - 194.3, 215.4, 194.3, stroke=1, fill=0)
    
    c.line(ox + 0,     H - (oy + 159.8), ox + 215.4, H - (oy + 159.8))
    c.line(ox + 0,     H - (oy + 168.2), ox + 215.4, H - (oy + 168.2))
    c.line(ox + 0,     H - (oy + 177.5), ox + 107.7, H - (oy + 177.5))
    c.line(ox + 0,     H - (oy + 185.9), ox + 107.7, H - (oy + 185.9))
    c.line(ox + 107.7, H - (oy + 159.8), ox + 107.7, H - (oy + 194.3))
    c.line(ox + 35.9,  H - (oy + 177.5), ox + 35.9,  H - (oy + 194.3))
    c.line(ox + 71.8,  H - (oy + 177.5), ox + 71.8,  H - (oy + 194.3))

    def desenhar_celula(txt, x, y, w, h, alinhamento_v="meio", sz=6.1, ent=6.1*1.25):
        fn = FONTES["Arial"]
        linhas = simpleSplit(str(txt or ""), fn, sz, w - 2)
        if alinhamento_v == "topo":
            b = y + ASCENT * sz
        else:
            b = y + h / 2.0 - (len(linhas) - 1) * ent / 2.0 + CENTRO * sz
        c.setFont(fn, sz)
        c.setFillColorRGB(0, 0, 0)
        for i, ln in enumerate(linhas):
            c.drawCentredString(ox + x + w / 2.0, H - (oy + b + i * ent), ln)

    desenhar_celula("LOCALIZAÇÃO", 0, 159.8, 107.7, 8.4)
    desenhar_celula("SERVIÇOS", 107.7, 159.8, 107.7, 8.4)
    desenhar_celula(rodovia, 0, 168.2, 107.7, 9.3)
    desenhar_celula(foto.get("servico", ""), 107.7, 168.2, 107.7, 26.1)
    desenhar_celula("ESTACA", 0, 177.5, 35.9, 8.4)
    desenhar_celula("KM", 35.9, 177.5, 35.9, 8.4)
    desenhar_celula("SITUAÇÃO", 71.8, 177.5, 35.9, 8.4)
    desenhar_celula(foto.get("estaca", ""), 0, 185.9, 35.9, 8.4)
    desenhar_celula(foto.get("km", ""), 35.9, 185.9, 35.9, 8.4)
    desenhar_celula(foto.get("situacao", ""), 71.8, 185.9, 35.9, 8.4)

def desenhar_assinaturas(c, H, campos):
    """Desenha o rodapé com as 3 linhas e nomes para assinatura."""
    c.setLineWidth(0.6)
    c.setStrokeColorRGB(0, 0, 0)
    c.line(91.0,  H - 770.7, 198.7, H - 770.7)
    c.line(234.5, H - 770.7, 387.6, H - 770.7)
    c.line(423.3, H - 770.7, 531.1, H - 770.7)

    def desenhar_celula_assina(txt, x, y, w, h):
        fn = FONTES["Arial"]
        sz = 6.7
        ent = 8.5
        linhas = simpleSplit(str(txt or ""), fn, sz, w - 2)
        b = y + ASCENT * sz
        c.setFont(fn, sz)
        c.setFillColorRGB(0, 0, 0)
        for i, ln in enumerate(linhas):
            c.drawCentredString(x + w / 2.0, H - (b + i * ent), ln)

    desenhar_celula_assina(campos.get("empresa", ""), 91.0, 772.1, 107.7, 20)
    desenhar_celula_assina(campos.get("supervisora", ""), 234.5, 772.1, 153.1, 20)
    desenhar_celula_assina(campos.get("fiscal", ""), 423.3, 772.1, 107.8, 20)

def gerar_relatorio_paginas_pdf(pdf_path, campos, paginas, logo_path=None):
    """
    Gera o PDF preservando rigorosamente as páginas explícitas do projeto e seus 6 slots por folha.
    """
    W, H = 595.2, 841.8  # A4 pt
    total_paginas = max(1, len(paginas))
    
    c = canvas.Canvas(pdf_path, pagesize=(W, H))
    c.setTitle(campos.get("titulo", "Relatório Fotográfico"))
    rodovia = campos.get("rodovia", "")
    km_base = campos.get("km_base", "198.8")
    m_estaca = campos.get("metros_estaca", "20.0")

    for pag_idx, pag in enumerate(paginas):
        # Cabeçalho da página
        desenhar_cabecalho(c, W, H, campos, logo_path, pag_idx + 1, total_paginas)

        # Slots da página (até 6 slots por folha)
        slots = getattr(pag, "slots", pag)
        for slot_idx, slot in enumerate(slots):
            if slot_idx >= len(POSICOES_FOTOS):
                break
            
            # Converte PhotoSlot ou dict
            if hasattr(slot, "esta_preenchido"):
                if not slot.ativo or not slot.esta_preenchido():
                    continue
                km_val = calcular_km(slot.estaca, km_base, m_estaca)
                foto_dict = {
                    "arquivo": slot.arquivo,
                    "estaca": slot.estaca,
                    "km": km_val,
                    "situacao": slot.situacao,
                    "servico": slot.servico,
                    "rotacao": getattr(slot, "rotacao", 0)
                }
            elif isinstance(slot, dict):
                if not slot.get("ativo", True) or not slot.get("arquivo"):
                    continue
                km_val = slot.get("km") or calcular_km(slot.get("estaca", ""), km_base, m_estaca)
                foto_dict = {
                    "arquivo": slot.get("arquivo", ""),
                    "estaca": slot.get("estaca", ""),
                    "km": km_val,
                    "situacao": slot.get("situacao", "DURANTE"),
                    "servico": slot.get("servico", ""),
                    "rotacao": slot.get("rotacao", 0)
                }
            else:
                continue

            ox, oy = POSICOES_FOTOS[slot_idx]
            desenhar_bloco_foto(c, H, ox, oy, foto_dict, rodovia)

        # Assinaturas
        desenhar_assinaturas(c, H, campos)
        c.showPage()

    c.save()
    return total_paginas

def gerar_relatorio_pdf(pdf_path, campos, fotos_indexadas, logo_path=None):
    """Gera o arquivo PDF com suporte a múltiplas páginas (compatibilidade para listas planas)."""
    W, H = 595.2, 841.8  # A4 pt
    
    total_fotos = len(fotos_indexadas)
    total_paginas = max(1, math.ceil(total_fotos / 6.0))
    
    c = canvas.Canvas(pdf_path, pagesize=(W, H))
    c.setTitle(campos.get("titulo", "Relatório Fotográfico"))
    
    rodovia = campos.get("rodovia", "")
    
    for pag_idx in range(total_paginas):
        inicio_idx = pag_idx * 6
        fim_idx = min(inicio_idx + 6, total_fotos)
        fotos_pagina = fotos_indexadas[inicio_idx:fim_idx]
        
        # Cabeçalho
        desenhar_cabecalho(c, W, H, campos, logo_path, pag_idx + 1, total_paginas)
        
        # Blocos de foto da página
        for i, foto in enumerate(fotos_pagina):
            ox, oy = POSICOES_FOTOS[i]
            desenhar_bloco_foto(c, H, ox, oy, foto, rodovia)
            
        # Assinaturas
        desenhar_assinaturas(c, H, campos)
        c.showPage()
        
    c.save()
    return total_paginas

def exportar_xml(xml_path, campos, fotos_indexadas, logo_path="assets/logo_dnit.png"):
    """Exporta o índice e variáveis em um XML compatível com o formato do projeto."""
    root = ET.Element("relatorio", nome="registro_fotografico", versao="1.0")
    ET.SubElement(root, "pagina", formato="A4", largura="595.2", altura="841.8", unidade="pt")
    
    estilos = ET.SubElement(root, "estilos")
    ET.SubElement(estilos, "estilo", id="titulo", fonte="Arial-Bold", tamanho="6.7")
    ET.SubElement(estilos, "estilo", id="rotulo", fonte="Arial-Bold", tamanho="5.5")
    ET.SubElement(estilos, "estilo", id="valor", fonte="Arial", tamanho="6.1")
    ET.SubElement(estilos, "estilo", id="legenda", fonte="Arial", tamanho="6.1")
    ET.SubElement(estilos, "estilo", id="assina", fonte="Arial", tamanho="6.7", entrelinha="8.5")
    ET.SubElement(estilos, "estilo", id="moldura", espessura="1.2")
    ET.SubElement(estilos, "estilo", id="fina", espessura="0.6")
    
    dados = ET.SubElement(root, "dados")
    for k, v in campos.items():
        if k in ("km_base", "metros_estaca"): continue
        campo_el = ET.SubElement(dados, "campo", id=k)
        campo_el.text = str(v or "")
        
    ET.SubElement(dados, "calculo", id="km", expressao=f"estaca * {campos.get('metros_estaca', 20)} / 1000 + {campos.get('km_base', 198.8)}", casas="2", separador_decimal=",")
    
    fotos_el = ET.SubElement(dados, "fotos")
    for i, f in enumerate(fotos_indexadas, 1):
        ET.SubElement(fotos_el, "foto", id=str(i), arquivo=f.get("arquivo", ""), estaca=str(f.get("estaca", "")), situacao=f.get("situacao", ""), servico=f.get("servico", ""))
        
    modelo = ET.SubElement(root, "modelo", id="bloco_foto")
    ET.SubElement(modelo, "imagem", x="0.1", y="0", largura="214.0", altura="158.6", arquivo="{foto.arquivo}")
    ET.SubElement(modelo, "retangulo", x="0", y="0", largura="215.4", altura="194.3", estilo="fina")
    ET.SubElement(modelo, "linha", x1="0", y1="159.8", x2="215.4", y2="159.8", estilo="fina")
    ET.SubElement(modelo, "linha", x1="0", y1="168.2", x2="215.4", y2="168.2", estilo="fina")
    ET.SubElement(modelo, "linha", x1="0", y1="177.5", x2="107.7", y2="177.5", estilo="fina")
    ET.SubElement(modelo, "linha", x1="0", y1="185.9", x2="107.7", y2="185.9", estilo="fina")
    ET.SubElement(modelo, "linha", x1="107.7", y1="159.8", x2="107.7", y2="194.3", estilo="fina")
    ET.SubElement(modelo, "linha", x1="35.9", y1="177.5", x2="35.9", y2="194.3", estilo="fina")
    ET.SubElement(modelo, "linha", x1="71.8", y1="177.5", x2="71.8", y2="194.3", estilo="fina")
    
    celulas = [
        ("LOCALIZAÇÃO", "0", "159.8", "107.7", "8.4"),
        ("SERVIÇOS", "107.7", "159.8", "107.7", "8.4"),
        ("{rodovia}", "0", "168.2", "107.7", "9.3"),
        ("{foto.servico}", "107.7", "168.2", "107.7", "26.1"),
        ("ESTACA", "0", "177.5", "35.9", "8.4"),
        ("KM", "35.9", "177.5", "35.9", "8.4"),
        ("SITUAÇÃO", "71.8", "177.5", "35.9", "8.4"),
        ("{foto.estaca}", "0", "185.9", "35.9", "8.4"),
        ("{foto.km}", "35.9", "185.9", "35.9", "8.4"),
        ("{foto.situacao}", "71.8", "185.9", "35.9", "8.4"),
    ]
    for c_txt, cx, cy, cw, ch in celulas:
        c_el = ET.SubElement(modelo, "celula", x=cx, y=cy, largura=cw, altura=ch, estilo="legenda")
        c_el.text = c_txt

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)
