"""Illustrated product diagrams, never screenshots of a user's private session."""
from html import escape

def shapes(step):
    items=[('rect',0,0,800,400,'#eef4f4'),('rect',28,24,772,376,'#ffffff'),('rect',28,24,772,67,'#142c3c'),('text',52,52,'Study Pilot C','#ffffff',17)]
    def rect(x,y,w,h,color):items.append(('rect',x,y,x+w,y+h,color))
    def text(x,y,value,size=18,color='#142c3c'):items.append(('text',x,y,value,color,size))
    if step==0:
        text(64,110,'01 / Mi cuenta',24);text(64,145,'Email + password from your web account',16)
        rect(64,165,430,42,'#eef4f4');text(78,193,'you@example.com',16)
        rect(64,218,430,42,'#eef4f4');text(78,246,'••••••••••••',18)
        rect(64,284,145,48,'#087f73');text(89,315,'Entrar',18,'#ffffff')
        rect(527,173,208,103,'#d9f5e7');text(546,211,'Acceso activo',18);text(546,241,'Ready to continue',14)
    elif step==1:
        text(64,113,'02 / Install once',24);text(64,149,'StudyPilotC-Setup.exe',20)
        rect(64,181,658,16,'#e8eeee');rect(64,181,480,16,'#087f73')
        text(64,233,'Python included · Google Chrome required',18)
        rect(64,271,270,49,'#087f73');text(83,302,'Abrir Study Pilot C',18,'#ffffff')
        text(420,299,'Desktop shortcut created',18)
    elif step==2:
        rect(44,81,712,43,'#edf2f5');text(63,110,'https://your-university.instructure.com',18)
        text(65,177,'03 / Use the new Chrome window',24)
        text(65,224,'Paste your Canvas activity link in this address bar.',18)
        text(65,266,'Sign in with your university. Then open the activity.',18)
        rect(65,301,667,43,'#d9f5e7');text(81,329,'Your university password stays in Chrome.',17)
    else:
        text(64,114,'04 / Your pace, your session',24)
        rect(64,142,315,149,'#eef4f4');text(85,176,'Seconds per question',17)
        text(85,234,'40 s',40);text(85,270,'Adjust live in Actividad',16)
        rect(406,142,315,149,'#142c3c');text(429,177,'SESSION STATUS',14,'#a7f3d0')
        text(429,221,'Analizando pregunta',20,'#ffffff');text(429,258,'Pause or stop at any time',15,'#ffffff')
        text(64,334,'Keep the questions open in the app’s Chrome.',18)
    return items

def svg(step):
    out=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 400" role="img"><title>Study Pilot setup illustration '+str(step+1)+'</title>']
    for item in shapes(step):
        if item[0]=='rect':
            _,x,y,x2,y2,c=item;out.append(f'<rect x="{x}" y="{y}" width="{x2-x}" height="{y2-y}" rx="10" fill="{c}"/>')
        else:
            _,x,y,t,c,size=item;out.append(f'<text x="{x}" y="{y}" fill="{c}" font-family="Arial,sans-serif" font-size="{size}">{escape(t)}</text>')
    return ''.join(out)+'</svg>'

def draw(canvas,step,width):
    canvas.delete('all');scale=width/800;canvas.configure(height=400*scale)
    for item in shapes(step):
        if item[0]=='rect':
            _,x,y,x2,y2,c=item;canvas.create_rectangle(x*scale,y*scale,x2*scale,y2*scale,fill=c,outline='')
        else:
            _,x,y,t,c,size=item;canvas.create_text(x*scale,y*scale,text=t,fill=c,font=('Segoe UI',max(9,int(size*scale))),anchor='sw')
