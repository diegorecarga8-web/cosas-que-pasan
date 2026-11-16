"""Dibujos para la segunda versión del cuaderno (8 hojas, fotos de 1200 × 1600)."""
import sys, pathlib
import colocar as C

C.BASE = 1200
C.SALIDA = pathlib.Path(__file__).resolve().parent / 'v2'
C.FOTOS = {
    'hoja1': '408f2ea6-image.jpg', 'hoja2': 'b10d3f73-image.jpg', 'hoja3': '9bebedc9-image.jpg',
    'hoja4': '1ae4ec9d-image.jpg', 'hoja5': '6660e434-image.jpg', 'hoja6': '1e9f610c-image.jpg',
    'hoja7': 'd3e99c03-image.jpg', 'hoja8': '06b868f4-image.jpg',
}
C.COLOCAR = [
    ('hoja1', 'hex', (100, 650, 470, 940)), ('hoja1', 'cube', (100, 965, 440, 1250)),
    ('hoja2', 'cubitos', (140, 300, 540, 560)), ('hoja2', 'box', (830, 660, 1130, 790)),
    ('hoja2', 'penta', (140, 860, 540, 1220)),
    ('hoja3', 'sqpyr', (130, 250, 520, 480)), ('hoja3', 'rectpyr', (120, 560, 560, 760)),
    ('hoja3', 'net_pyr', (110, 860, 560, 1200)),
    ('hoja4', 'cyl', (110, 260, 500, 520)), ('hoja4', 'cyl2', (110, 540, 440, 690)),
    ('hoja4', 'discos', (110, 710, 470, 1000)), ('hoja4', 'net_cyl', (100, 1080, 520, 1390)),
    ('hoja5', 'cone', (110, 230, 480, 560)), ('hoja5', 'cone2', (130, 620, 460, 900)),
    ('hoja5', 'net_cone', (110, 950, 480, 1250)),
    ('hoja6', 'sphere', (120, 240, 560, 560)), ('hoja6', 'sph2', (120, 630, 560, 950)),
    ('hoja6', 'gen', (90, 1250, 600, 1450)),
    ('hoja7', 'hemicone', (120, 260, 520, 560)), ('hoja7', 'cylcone', (130, 600, 470, 870)),
    ('hoja8', 'net_box', (110, 140, 500, 400)), ('hoja8', 'net_penta', (100, 470, 530, 760)),
]
if __name__ == '__main__':
    C.main(sys.argv[1])
