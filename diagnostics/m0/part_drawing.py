from pathlib import Path
from cadgen import read_step
from cadgen.eng_drawing import Sheet, eng_drawing

ROOT = Path(__file__).resolve().parent

@eng_drawing(out='out/part-metric.pdf')
def part_drawing():
    shape = read_step(ROOT / 'out/part.step')
    sheet = Sheet('A4', scale=0.1, title='INTEGRATION SPIKE', part_number='part', revision='M0', units='mm', notes=['METRIC A4 LANDSCAPE. NOMINAL DIMENSIONS.'])
    top, front, right = sheet.three_views(shape)
    sheet.view(shape, 'iso', at=(225, 145), scale=0.08, label='ISOMETRIC 1:12.5')
    top.overall()
    front.overall()
    right.overall()
    return sheet

if __name__ == '__main__':
    part_drawing()
