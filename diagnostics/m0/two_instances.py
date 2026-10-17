from cadgen import build123d as bd, step

@step(out='out/two-instances.step')
def two_instances():
    base = bd.Box(100, 60, 18, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER))
    a = base.moved(bd.Location((-60, 0, 0)))
    b = base.moved(bd.Location((60, 0, 0)))
    a.label = 'panel_left'
    b.label = 'panel_right'
    return bd.Compound(children=[a, b], label='two_instances')

if __name__ == '__main__':
    two_instances()
