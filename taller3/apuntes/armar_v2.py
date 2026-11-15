"""Arma apuntes_v2.html: mismo estilo de cuaderno que apuntes.html, con el contenido de contenido_v2.html."""
import pathlib, re
import figuras as F

AQUI = pathlib.Path(__file__).parent
base = (AQUI / 'apuntes.html').read_text()
contenido = (AQUI / 'contenido_v2.html').read_text()

# índice original de cada figura (para conservar el tamaño ya ajustado en SC)
FIGS = {
    'hex': (1, F.fig_hex), 'sqpyr': (2, F.fig_sqpyr), 'cone': (3, lambda: F.fig_cone().svg()),
    'cube': (4, F.fig_cube), 'cyl': (5, lambda: F.fig_cyl().svg()), 'gen': (6, F.fig_gen),
    'sphere': (7, F.fig_sphere), 'cubitos': (8, F.fig_cubitos), 'discos': (9, F.fig_discos),
    'rectpyr': (10, F.fig_rectpyr), 'cone2': (11, F.fig_cone2), 'cyl2': (12, F.fig_cyl2),
    'sph2': (13, F.fig_sph2), 'box': (14, F.fig_box), 'penta': (15, F.fig_penta),
    'hemicone': (16, F.fig_hemicone), 'cylcone': (17, F.fig_cylcone), 'net_box': (18, F.net_box),
    'net_cyl': (19, F.net_cyl), 'net_cone': (20, F.net_cone), 'net_pyr': (21, F.net_pyr),
    'net_penta': (22, F.net_penta),
}

def figura(m):
    idx, fn = FIGS[m.group(1)]
    F.CUR[0] = idx
    return fn()

contenido = re.sub(r'\{\{fig:(\w+)\}\}', figura, contenido)

inicio = base.index('<!-- ================= HOJA 1')
fin = base.index('<svg width="0" height="0" style="position:absolute">\n  <defs>\n    <filter id="ink"')
hojas = [h.strip() for h in contenido.split('<!-- @@HOJA -->')[1:]]
paginas = []
for i, h in enumerate(hojas, 1):
    paginas.append(f'''<!-- ================= HOJA {i} ================= -->
<div class="page">
  <div class="datebox"><span style="top:3mm">AA</span><span style="top:17mm">MM</span><span style="top:31mm">DD</span></div><div class="strip"></div>
  <div class="grid"></div>
  <div class="content">
{h}
  </div>
  <div class="pnum">{i}</div>
</div>
''')
salida = base[:inicio] + '\n'.join(paginas) + '\n\n' + base[fin:]
(AQUI / 'apuntes_v2.html').write_text(salida)
print('hojas:', len(hojas))
