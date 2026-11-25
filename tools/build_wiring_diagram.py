"""Build an editable SVG wiring plan with embedded component illustrations.

Component artwork is generated separately at high resolution. Labels,
pin assignments and electrical nets are SVG elements, never regenerated pixels.
Run from any directory with Python's standard library.
"""
import base64
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT_DIRECTORY = ROOT / "docs/diagrams/components"
OUTPUT = ROOT / "docs/fnc-fogger-wiring.svg"
COLORS = {"24v": "#ed7b15", "5v": "#da343b", "3v3": "#da343b",
          "gnd": "#202c38", "sda": "#1767d2", "scl": "#efc526",
          "gate": "#7737be", "tach": "#16833d", "pwm": "#1767d2"}


def build():
    components = json.loads((COMPONENT_DIRECTORY / "artwork.json").read_text(encoding="utf-8"))
    artwork = []
    for name, metadata in components.items():
        data = base64.b64encode((COMPONENT_DIRECTORY / metadata["file"]).read_bytes()).decode("ascii")
        width, height = metadata["size"]
        mime_type = "image/png" if metadata["file"].endswith(".png") else "image/webp"
        artwork.append(f'<image id="{name}" width="{width}" height="{height}" xlink:href="data:{mime_type};base64,{data}"/>')
    artwork = "\n".join(artwork)
    elements = [f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1600" height="1090" viewBox="0 0 1600 1090" role="img" aria-labelledby="title desc">
<title id="title">fnc-fogger · ESP32-C3 wiring · GPIO3 gate · firmware 3.4.3</title>
<desc id="desc">Six panels show 24V power with a 5V buck converter, ESP32-C3 pin connections, parallel I2C sensors, Noctua fan pinout, IRLB8721 fogger switching and implemented firmware behavior. Component illustrations are embedded; all wiring and labels are vector elements. Gate GPIO3, PWM GPIO10, tach GPIO7, SDA GPIO0, SCL GPIO1.</desc>
<defs><linearGradient id="header" x2="1" y2="1"><stop stop-color="#1253a2"/><stop offset="1" stop-color="#173e77"/></linearGradient>
{artwork}
</defs><rect width="1600" height="1090" fill="#f2f6fb"/>
<g font-family="Segoe UI, Arial, sans-serif" fill="#17324e">''']

    def text(x, y, value, size=18, color="#17324e", weight="400", anchor="start"):
        elements.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{escape(value)}</text>')

    def box(x, y, w, h, fill="#fff", stroke="#d6e1ee", radius=12, dashed=False):
        dash = ' stroke-dasharray="7 5"' if dashed else ''
        elements.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"{dash}/>')

    def panel(x, y, w, h, number, title):
        box(x, y, w, h)
        box(x, y, w, 52, 'url(#header)', 'none')
        box(x+12, y+9, 34, 34, '#fff', 'none', 8)
        text(x+29, y+34, str(number), 24, '#173e77', '700', 'middle')
        text(x+60, y+34, title, 25, '#fff', '700')

    def component(name, x, y, width, height):
        view = ' '.join(str(n) for n in components[name]["view_box"])
        elements.append(f'<svg x="{x}" y="{y}" width="{width}" height="{height}" viewBox="{view}" preserveAspectRatio="xMidYMid meet"><use xlink:href="#{name}"/></svg>')

    def wire(points, color, dashed=False, width=5):
        coords = ' '.join(f'{x},{y}' for x,y in points)
        dash = ' stroke-dasharray="8 6"' if dashed else ''
        elements.append(f'<polyline points="{coords}" fill="none" stroke="{COLORS.get(color,color)}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"{dash}/>')

    def dot(x,y,color,radius=5):
        elements.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{COLORS.get(color,color)}"/>')

    def note(x,y,w,lines):
        box(x,y,w,18+23*len(lines),'#edf4fc','none',8)
        for i,line in enumerate(lines): text(x+12,y+25+23*i,line,16)

    text(30,51,'fnc-fogger',43,weight='700')
    text(284,51,'Wiring Diagram',36,weight='600')
    text(1570,51,'ESP32-C3 SuperMini · 24V fan / 24V fogger · firmware 3.4.3 · REV 08 · 23 Nov 2026',18,color='#526b84',anchor='end')

    panel(20,115,520,490,1,'24-V Supply')
    text(46,204,'24V DC',21,COLORS['24v'],'700')
    text(46,378,'GND',21,COLORS['gnd'],'700')
    component('buck',210,290,144,104)
    text(282,275,'XZG buck · 24V → 5V',18,weight='600',anchor='middle')
    text(195,332,'IN+',14,anchor='middle')
    text(392,332,'OUT+',14,anchor='end')
    wire([(55,224),(145,224),(145,308),(222,308)],'24v')
    wire([(145,308),(145,190),(300,190)],'24v');dot(145,308,'24v',7)
    dot(145,190,'24v',7)
    wire([(145,224),(300,224)],'24v');dot(145,224,'24v',7)
    text(310,230,'Fogger +',18,COLORS['24v'],'600')
    text(310,196,'Fan pin 2',18,COLORS['24v'],'600')
    wire([(341,308),(400,308),(400,295),(505,295)],'5v')
    text(426,282,'5V ESP32',17,COLORS['5v'],'600')
    # IN− and OUT− share the module ground; no redundant external loop.
    wire([(55,396),(222,396),(341,396),(500,396)],'gnd')
    wire([(222,374),(222,396)],'gnd')
    wire([(341,374),(341,396)],'gnd')
    text(222,429,'IN−',16,anchor='middle');text(341,429,'OUT−',16,anchor='middle')
    for y,label in [(462,'I² GND'),(499,'Fan GND'),(536,'Mosfet source')]:
        wire([(111,396),(111,y),(194,y)],'gnd');dot(111,y,'gnd',7);text(210,y+6,label,18)
    text(500,426,'ESP32 GND',18,COLORS['gnd'],'600','end')
    for x in (111,222,341):
        dot(x,396,'gnd',7)


    panel(555,115,430,490,2,'ESP32-C3 SuperMini')
    component('esp32-c3',682,200,176,375)
    left = [('GPIO0 / SDA','sda'),('GPIO1 / SCL','scl'),('GPIO2',None),('GPIO3 / GATE','gate'),('GPIO4',None),('3V3','3v3'),('GND','gnd'),('5V / BUCK +','5v')]
    right = [('GPIO21',None),('GPIO20',None),('GPIO10 / PWM','pwm'),('GPIO9',None),('GPIO8',None),('GPIO7 / TACH','tach'),('GPIO6',None),('GPIO5',None)]
    # The two enclosing panels keep each pin row aligned and easy to scan.
    box(572,252,108,246,'#f6f9fd','#d6e1ee',10)
    box(860,252,108,246,'#f6f9fd','#d6e1ee',10)
    for labels, x1, x2, label_x, label_width in [
        (left,680,696,578,96), (right,844,860,866,96)
    ]:
        for index, (label, signal) in enumerate(labels):
            y = 273 + 29.2 * index
            color = COLORS.get(signal, '#9aa7b6')
            wire([(x1,y),(x2,y)],color,width=5)
            fill = color if signal else '#e7edf4'
            foreground = '#263746' if signal in (None,'scl') else '#fff'
            box(label_x,y-14,label_width,28,fill,'none',6)
            text(label_x+label_width/2,y+5,label,12,foreground,
                 '700' if signal else '400','middle')

    panel(1000,115,580,490,3,'Sensors · shared I²C bus')
    sensors=[(1160,'SCD41','CO₂ · 0x62','scd41'),(1330,'SHT45','RH / Temp · 0x44','sht45'),(1500,'SHTC3','Ambient · 0x70','shtc3')]
    box(1428,178,144,354,'#fbfcff','#9eafc4',10,True)
    text(1500,202,'OPTIONAL',14,'#526b84','700','middle')
    for center,name,detail,asset in sensors:
        text(center,233,name,23,weight='700',anchor='middle')
        text(center,258,detail,16,anchor='middle')
        component(asset,center-65,273,130,114)
    buses=[('GND','gnd',417),('3V3','3v3',448),('SDA · GPIO0','sda',479),('SCL · GPIO1','scl',510)]
    qwiic_pin_offsets = {'gnd': -20, '3v3': -7, 'sda': 7, 'scl': 21}
    for label,signal,y in buses:
        text(1021,y+6,label,15,COLORS[signal] if signal!='scl' else '#665200','600')
        wire([(1120,y),(1552,y)],signal)
        for sensor_index,(center,_,_,_) in enumerate(sensors):
            x=center+qwiic_pin_offsets[signal]
            wire([(x,377),(x,y)],signal,sensor_index==2);dot(x,y,signal)


    panel(20,625,500,444,4,'Noctua NF-A4x10 24V PWM')
    component('noctua',50,711,270,230)
    pins=[('1','gnd','GND','Common GND'),('2','scl','24V','Supply 24V'),('3','tach','TACH','GPIO7'),('4','pwm','PWM','GPIO10')]
    for i,(number,color,label,target) in enumerate(pins):
        y=731+i*62
        elements.append(f'<circle cx="340" cy="{y}" r="15" fill="{COLORS[color]}"/>')
        text(340,y+6,number,18,'#172838' if color=='scl' else '#fff','700','middle')
        text(367,y+5,label,20,weight='700');text(367,y+27,target,17)
    note(38,984,464,['PWM: 3.3V push-pull · 25 kHz','Tach: 2 pulses / revolution · internal 3.3V pull-up'])

    panel(535,625,510,444,5,'Fogger · IRLB8721')
    component('irlb8721',583,725,107,192)
    for y,label,target,color in [(754,'GPIO3','Gate','gate'),(809,'Fogger −','Drain','gnd'),(864,'GND','Source','gnd'),(919,'24V','Fogger','24v')]:
        box(710,y-23,117,36,'#fff',COLORS[color],6)
        text(768,y+2,label,20,COLORS[color],'700','middle')
        wire([(827,y-5),(906,y-5)],color);text(917,y+1,target,20)
    for x, label in [(616,'G'),(636,'D'),(656,'S')]:
        text(x,943,label,20,weight='700',anchor='middle')
    note(553,975,474,['HIGH = ON · LOW = OFF','24V Fogger with integrated driver.'])

    panel(1060,625,520,444,6,'Operation · firmware + OTA')
    text(1083,703,'IMPLEMENTED',14,'#167d69','700')
    for i,line in enumerate(['Sensor sampling + local measurement buffer','Fan PWM / RPM + manual fogger output','Manual Mode: independent 0–100% outputs','Manual outputs stop on device Wi-Fi loss','First installation: USB · later updates: OTA']):
        text(1083,738+i*34,'• '+line,17)
    box(1080,946,480,95,'#fff4e3','none',8)
    text(1094,973,'PI CONTROL',17,'#8d591b','700')
    text(1094,1000,'CO₂ PI controls the fan.',16)
    text(1094,1024,'Humidity PI controls the fogger.',16)

    elements.append('</g></svg>')
    OUTPUT.write_text('\n'.join(elements),encoding='utf-8')
    print(OUTPUT)


if __name__ == '__main__':
    build()
