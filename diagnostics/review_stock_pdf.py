"""Independent saved-PDF text bounds and contact sheets for visual inspection."""
import argparse
import json
from pathlib import Path
from PIL import Image,ImageDraw
from pypdf import PdfReader
from reportlab.pdfbase.pdfmetrics import stringWidth


def main():
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path);args=parser.parse_args()
    contacts=args.root/'review';contacts.mkdir(exist_ok=True)
    findings=[];total=0
    for folder in sorted(args.root.glob('bookcase-*')):
        for index,page in enumerate(PdfReader(folder/'stock-layout.pdf').pages,1):
            width,height=float(page.mediabox.width),float(page.mediabox.height)
            def visit(text,cm,tm,font,size):
                value=text.strip('\r\n')
                if not value:return
                name=str(font.get('/BaseFont','/Helvetica')).lstrip('/') if font else 'Helvetica'
                try:extent=stringWidth(value,name,size)
                except KeyError:extent=stringWidth(value,'Helvetica',size)
                x=cm[0]*tm[4]+cm[2]*tm[5]+cm[4];y=cm[1]*tm[4]+cm[3]*tm[5]+cm[5]
                if size<8.9 or x<23.9 or y<23.9 or x+extent>width-23.9 or y+size>height-23.9:
                    findings.append({'fixture':folder.name,'page':index,'text':value,'font_size':size,'x':x,'y':y,'right':x+extent,'page_width':width,'page_height':height})
            page.extract_text(visitor_text=visit);total+=1
        paths=sorted((args.root/'rendered'/folder.name).glob('*.png'))
        for start in range(0,len(paths),6):
            canvas=Image.new('RGB',(1800,1620),'#d6d6d6');draw=ImageDraw.Draw(canvas)
            for offset,path in enumerate(paths[start:start+6]):
                image=Image.open(path).convert('RGB');image.thumbnail((590,765))
                x=(offset%3)*600+5;y=(offset//3)*810+25
                canvas.paste(image,(x,y));draw.text((x,y-17),path.name,fill='black')
            canvas.save(contacts/f'{folder.name}-{start//6+1}.png')
    (contacts/'bounds-evidence.json').write_text(json.dumps({'pages':total,'status':'passed' if not findings else 'failed','findings':findings},indent=2))
    print(json.dumps({'pages':total,'bounds_status':'passed' if not findings else 'failed','findings':findings[:6],'contact_sheets':str(contacts)}))
    if findings:raise SystemExit(1)


if __name__=='__main__':main()
