from pathlib import Path
from cadgen import build123d as bd, step, glb

@step(out='out/asymmetric.step')
@glb(out='out/asymmetric.glb')
def asymmetric():
    panel = bd.Box(100, 60, 18, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER))
    hole = bd.Cylinder(4, 18, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER)).moved(bd.Location((20, 10, 0)))
    part = panel - hole
    part.label = 'asymmetric'
    return part

if __name__ == '__main__':
    asymmetric()
