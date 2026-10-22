#!/usr/bin/env python3
"""Renderiza um modelo XML de relatório (ver relatorio_fotografico.xml) em PDF.

Uso:  python render_xml.py relatorio_fotografico.xml saida.pdf
Requer: reportlab  (pip install reportlab)
Origem das coordenadas do XML: canto superior esquerdo; unidade: pt.
"""
import ast, operator, os, re, sys
import xml.etree.ElementTree as ET
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

FONTES = {"Arial": "Helvetica", "Arial-Bold": "Helvetica-Bold"}
ASCENT, CENTRO = 0.905, 0.3465   # linha de base a partir do topo / do centro da caixa

# ---- avaliador aritmético seguro (para <calculo expressao="...">) ----
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.USub: operator.neg}
def calc(expr, variaveis):
    def ev(n):
        if isinstance(n, ast.Expression): return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)): return n.value
        if isinstance(n, ast.Name): return float(variaveis[n.id])
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS: return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS: return _OPS[type(n.op)](ev(n.operand))
        raise ValueError("expressão não permitida: " + expr)
    return ev(ast.parse(expr, mode="eval"))

def carregar(caminho):
    raiz = ET.parse(caminho).getroot()
    base = os.path.dirname(os.path.abspath(caminho))
    pg = raiz.find("pagina")
    estilos = {e.get("id"): dict(e.attrib) for e in raiz.find("estilos")}
    dados = raiz.find("dados")
    campos = {c.get("id"): (c.text or "") for c in dados.findall("campo")}
    calculos = [c.attrib for c in dados.findall("calculo")]
    fotos = {}
    for f in dados.find("fotos"):
        reg = dict(f.attrib)
        for c in calculos:
            v = calc(c["expressao"], reg)
            s = f"{v:.{int(c.get('casas', 2))}f}"
            reg[c["id"]] = s.replace(".", c.get("separador_decimal", "."))
        fotos[reg["id"]] = reg
    modelos = {m.get("id"): m for m in raiz.findall("modelo")}
    return raiz, base, pg, estilos, campos, fotos, modelos

def subst(txt, campos, foto):
    def r(m):
        k = m.group(1)
        if k.startswith("foto."): return foto[k[5:]]
        return campos[k]
    return re.sub(r"\{([\w.]+)\}", r, txt or "")

def renderizar(xml_path, pdf_path):
    raiz, base, pg, estilos, campos, fotos, modelos = carregar(xml_path)
    W, H = float(pg.get("largura")), float(pg.get("altura"))
    c = canvas.Canvas(pdf_path, pagesize=(W, H))
    c.setTitle(campos.get("titulo", "Relatório"))

    def fonte(est):
        e = estilos[est]
        return FONTES.get(e["fonte"], e["fonte"]), float(e["tamanho"]), float(e.get("entrelinha", float(e["tamanho"]) * 1.25))
    def traco(est):
        c.setLineWidth(float(estilos[est]["espessura"])); c.setStrokeColorRGB(0, 0, 0)
    f_ = lambda e, a: float(e.get(a))

    def desenhar(el, ox, oy, foto):
        t = el.tag
        if t == "linha":
            traco(el.get("estilo"))
            c.line(ox + f_(el, "x1"), H - (oy + f_(el, "y1")), ox + f_(el, "x2"), H - (oy + f_(el, "y2")))
        elif t == "retangulo":
            traco(el.get("estilo"))
            h = f_(el, "altura")
            c.rect(ox + f_(el, "x"), H - (oy + f_(el, "y")) - h, f_(el, "largura"), h, stroke=1, fill=0)
        elif t == "imagem":
            arq = subst(el.get("arquivo"), campos, foto)
            h = f_(el, "altura")
            c.drawImage(os.path.join(base, arq), ox + f_(el, "x"), H - (oy + f_(el, "y")) - h,
                        f_(el, "largura"), h, mask="auto")
        elif t == "texto":
            fn, sz, _ = fonte(el.get("estilo"))
            txt = subst(el.text, campos, foto)
            base_y = H - (oy + f_(el, "y") + ASCENT * sz)
            c.setFont(fn, sz); c.setFillColorRGB(0, 0, 0)
            x = ox + f_(el, "x")
            if el.get("alinhamento") == "centro": c.drawCentredString(x, base_y, txt)
            elif el.get("alinhamento") == "direita": c.drawRightString(x, base_y, txt)
            else: c.drawString(x, base_y, txt)
        elif t == "celula":
            fn, sz, ent = fonte(el.get("estilo"))
            txt = subst(el.text, campos, foto)
            x, y, w, h = ox + f_(el, "x"), oy + f_(el, "y"), f_(el, "largura"), f_(el, "altura")
            linhas = simpleSplit(txt, fn, sz, w - 2)
            if el.get("alinhamento_vertical", "meio") == "topo":
                b = y + ASCENT * sz
            else:
                b = y + h / 2 - (len(linhas) - 1) * ent / 2 + CENTRO * sz
            c.setFont(fn, sz); c.setFillColorRGB(0, 0, 0)
            for i, ln in enumerate(linhas):
                c.drawCentredString(x + w / 2, H - (b + i * ent), ln)
        elif t == "instancia":
            m = modelos[el.get("modelo")]
            ft = fotos[el.get("foto")]
            for sub in m:
                desenhar(sub, ox + f_(el, "x"), oy + f_(el, "y"), ft)

    for el in raiz.find("layout"):
        desenhar(el, 0, 0, {})
    c.showPage(); c.save()

if __name__ == "__main__":
    if len(sys.argv) != 3: sys.exit(__doc__)
    renderizar(sys.argv[1], sys.argv[2])
