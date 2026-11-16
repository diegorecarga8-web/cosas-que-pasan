"""Pone los dibujos de figuras.py sobre las fotos del cuaderno.

Uso: python3 colocar.py <carpeta_de_trabajo>
Cada entrada de COLOCAR dice: foto, figura y el recuadro libre (x0, y0, x1, y1) medido
sobre la foto a 1500 × 2000; el dibujo se ajusta a ese recuadro y se funde con el papel.
"""
import json, pathlib, subprocess, sys
from PIL import Image, ImageChops, ImageFilter

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / 'apuntes'))
import figuras as F  # noqa: E402

UP = pathlib.Path('/root/.claude/uploads/9a3c6f49-df32-5093-811b-98a3e8842089')
FOTOS = {
    'hoja1': 'fcaa38f0-image.jpg', 'hoja2': '80feb8aa-image.jpg', 'hoja3': 'de2ebbd4-image.jpg',
    'hoja4': 'b563319b-image.jpg', 'hoja5': '73585f76-image.jpg', 'hoja6': '6f933c47-image.jpg',
}
FIGS = {
    'hex': (1, F.fig_hex), 'sqpyr': (2, F.fig_sqpyr), 'cone': (3, lambda: F.fig_cone().svg()),
    'cube': (4, F.fig_cube), 'cyl': (5, lambda: F.fig_cyl().svg()), 'sphere': (7, F.fig_sphere),
    'cubitos': (8, F.fig_cubitos), 'discos': (9, F.fig_discos), 'rectpyr': (10, F.fig_rectpyr),
    'cone2': (11, F.fig_cone2), 'cyl2': (12, F.fig_cyl2), 'sph2': (13, F.fig_sph2), 'box': (14, F.fig_box),
    'penta': (15, F.fig_penta), 'hemicone': (16, F.fig_hemicone), 'cylcone': (17, F.fig_cylcone),
    'net_box': (18, F.net_box), 'net_cyl': (19, F.net_cyl),
}
COLOCAR = [
    ('hoja1', 'hex', (95, 350, 360, 830)), ('hoja1', 'sqpyr', (95, 990, 375, 1330)),
    ('hoja1', 'cone', (110, 1455, 395, 1800)),
    ('hoja2', 'cube', (205, 300, 515, 640)), ('hoja2', 'cyl', (215, 790, 500, 1110)),
    ('hoja2', 'sphere', (205, 1240, 505, 1560)),
    ('hoja3', 'cubitos', (760, 470, 1310, 900)), ('hoja3', 'discos', (720, 1005, 1300, 1290)),
    ('hoja3', 'rectpyr', (660, 1390, 1320, 1720)),
    ('hoja4', 'cone2', (690, 280, 1100, 640)), ('hoja4', 'cyl2', (700, 730, 1100, 1010)),
    ('hoja4', 'sph2', (700, 1100, 1050, 1440)), ('hoja4', 'box', (640, 1590, 1300, 1750)),
    ('hoja5', 'penta', (820, 300, 1340, 650)), ('hoja5', 'hemicone', (900, 800, 1340, 1160)),
    ('hoja5', 'cylcone', (900, 1360, 1340, 1700)),
    ('hoja6', 'net_box', (720, 340, 1340, 720)), ('hoja6', 'net_cyl', (720, 880, 1340, 1240)),
]
FILTROS = '''<svg width="0" height="0" style="position:absolute"><defs>
<filter id="rough" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="4" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="2.6" xChannelSelector="R" yChannelSelector="G"/></filter>
<filter id="gr" x="-3%" y="-3%" width="106%" height="106%"><feTurbulence type="fractalNoise" baseFrequency="0.55" numOctaves="2" seed="9" result="g"/><feColorMatrix in="g" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  2.4 0 0 0 -0.45" result="ga"/><feComposite in="SourceGraphic" in2="ga" operator="in"/><feGaussianBlur stdDeviation="0.5"/></filter>
</defs></svg>'''
NODE = r'''
const {chromium}=require('playwright');
(async()=>{const [html,out,ids]=process.argv.slice(2);const b=await chromium.launch();
const p=await b.newPage({deviceScaleFactor:3});await p.goto('file://'+html);await p.evaluate(()=>document.fonts.ready);
for(const id of JSON.parse(ids)){const e=await p.$('#'+id);await e.screenshot({path:out+'/'+id+'.png',omitBackground:true});}
await b.close();})();
'''

def main(trabajo):
    trabajo = pathlib.Path(trabajo); trabajo.mkdir(parents=True, exist_ok=True)
    nombres = sorted({f for _, f, _ in COLOCAR})
    partes = []
    for n in nombres:
        idx, fn = FIGS[n]; F.CUR[0] = idx
        partes.append(f'<div id="{n}" style="display:inline-block;filter:url(#gr);padding:22px">{fn()}</div><br>')
    html = trabajo / 'figs.html'
    html.write_text('<html><head><style>@font-face{font-family:"Handlee";src:url("' + str(AQUI.parent / 'apuntes/fonts/Handlee-Regular.ttf') +
                    '")} svg text{font-family:"Handlee"} svg.sk{overflow:visible}</style></head><body style="margin:0;background:transparent">' + FILTROS + ''.join(partes) + '</body></html>')
    (trabajo / 'figs.js').write_text(NODE)
    subprocess.run(['node', str(trabajo / 'figs.js'), str(html), str(trabajo), json.dumps(nombres)], check=True)

    fotos = {}
    for hoja, n, (x0, y0, x1, y1) in COLOCAR:
        if hoja not in fotos:
            fotos[hoja] = Image.open(UP / FOTOS[hoja]).convert('RGB')
        ph = fotos[hoja]; k = ph.width / 1500
        x0, y0, x1, y1 = [round(v * k) for v in (x0, y0, x1, y1)]
        d = Image.open(trabajo / f'{n}.png').convert('RGBA')
        d = d.crop(d.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox())
        s = min((x1 - x0) / d.width, (y1 - y0) / d.height)
        d = d.resize((max(1, round(d.width * s)), max(1, round(d.height * s))), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.5))
        ox, oy = x0 + ((x1 - x0) - d.width) // 2, y0 + ((y1 - y0) - d.height) // 2
        r, g, b, a = d.split()
        tinta = Image.merge('RGB', (r, g, b)).point(lambda v: min(255, int(v * 0.78 + 24)))
        capa = Image.composite(tinta, Image.new('RGB', d.size, (255, 255, 255)), a.filter(ImageFilter.MaxFilter(3)).point(lambda v: int(v * 0.92)))
        zona = ph.crop((ox, oy, ox + d.width, oy + d.height))
        ph.paste(ImageChops.multiply(zona, capa), (ox, oy))
    for hoja, ph in fotos.items():
        ph.save(AQUI / f'{hoja}_con_dibujos.jpg', quality=92)
        print('ok', hoja)

if __name__ == '__main__':
    main(sys.argv[1])
