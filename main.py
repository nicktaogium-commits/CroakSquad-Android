"""Croak Squad Android preview client (Kivy). Source-derived V17 maps and TCP protocol.
This is a port prototype, NOT the original Windows renderer or a finished APK.
"""
import os, math, json, socket, threading, queue, time
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Ellipse, Line
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window
from kivy.utils import platform
import maps

BASE=os.path.dirname(os.path.abspath(__file__))
GW,GH=1100.,680.
REACH=128

def rect_hit(a,b):return maps.intersects(a,b)

class CroakView(Widget):
    def __init__(self,game,**kwargs):
        super().__init__(**kwargs);self.game=game
        self.textures=[]
        for i in range(6):
            try:self.textures.append(CoreImage(os.path.join(BASE,'assets',f'frog_{i}.png')).texture)
            except Exception:self.textures.append(None)
        self.bind(pos=lambda *_:self.paint(),size=lambda *_:self.paint())

    def paint(self):
        g=self.game;self.canvas.clear()
        if g.mode not in ('play','lobby'):return
        factor=min(self.width/GW,self.height/GH)
        ox=self.x+(self.width-GW*factor)/2; oy=self.y+(self.height-GH*factor)/2
        def xy(x,y,w=0,h=0):return (ox+x*factor,oy+(GH-y-h)*factor)
        def box(x,y,w,h,c):
            Color(*c);Rectangle(pos=xy(x,y,w,h),size=(w*factor,h*factor))
        with self.canvas:
            box(0,0,GW,GH,(.98,.90,.86,1))
            if g.mode=='lobby':return
            stage=g.stage;level=maps.LEVELS[stage];camera=g.camera
            # Background stripes indicate parallax without large GPU textures.
            box(0,515,1100,165,(.91,.81,.72,1))
            for x,y,w,h in maps.solids(stage,g.elapsed):
                sx=x-camera
                if -w-40<sx<1140:
                    box(sx,y,w,h,(.88,.69,.43,1));box(sx,y,w,7,(.51,.76,.58,1))
            platforms,saws,crushers=maps.moving_objects(stage,g.elapsed)
            for x,y,w,h in platforms:
                box(x-camera,y,w,h,(.48,.75,.71,1))
            for x,y,r in saws:
                if -r<x-camera<1100+r:
                    Color(.63,.39,.56,1);Ellipse(pos=xy(x-camera-r,y-r,r*2,r*2),size=(r*2*factor,r*2*factor))
                    Color(.98,.68,.70,1);Ellipse(pos=xy(x-camera-r*.7,y-r*.7,r*1.4,r*1.4),size=(r*1.4*factor,r*1.4*factor))
            for x,y,w,h in crushers:box(x-camera,y,w,h,(.75,.40,.55,1))
            for x,y,w in level['spikes']:
                for dx in range(0,int(w),20):
                    Color(.55,.34,.49,1)
                    px,py=xy(x-camera+dx, y, 20,40)
                    from kivy.graphics import Triangle
                    Triangle(points=[px,py,px+10*factor,py+40*factor,px+20*factor,py])
            for i,(x,_) in enumerate(level['checkpoints']):
                box(x-camera,530,5,60,(.30,.46,.37,1))
                box(x-camera+5,530,27,17,(.36,.78,.52,1) if i<=g.cp else (.77,.70,.60,1))
            box(level['goal']-camera,485,7,105,(.49,.40,.55,1))
            box(level['goal']-camera+7,485,52,25,(.98,.66,.73,1))
            for pid,p in g.players.items():
                if p['heldby']:continue
                x=p['x']-camera;y=p['y']
                if x<-100 or x>1200:continue
                tx=self.textures[p['color']%6]
                if tx:
                    Color(1,1,1,1);Rectangle(texture=tx,pos=xy(x-26,y-32,52,60),size=(52*factor,60*factor))
                else:
                    Color(.49,.82,.61,1);Ellipse(pos=xy(x-24,y-24,48,48),size=(48*factor,48*factor))
            if g.tongue:
                pid,tx,ty,end=g.tongue
                if pid in g.players and time.monotonic()<end:
                    p=g.players[pid];sx=p['x']-camera;sy=p['y'];frac=max(0,min(1,(end-time.monotonic())/.46))
                    ext=min(1,(1-frac)*3) if frac>.66 else min(1,frac*3)
                    tipx=sx+(tx-p['x'])*ext;tipy=sy+(ty-p['y'])*ext
                    Color(1,.35,.54,1)
                    a=xy(sx+p['face']*16,sy,0,0);b=xy(tipx,tipy,0,0)
                    Line(points=[*a,*b],width=max(3,8*factor),cap='round')

class CroakRoot(FloatLayout):
    def __init__(self,**kw):
        super().__init__(**kw)
        self.mode='menu';self.stage=0;self.elapsed=0.;self.camera=0.;self.cp=0;self.unlocked=1
        self.players={};self.active='p1';self.axis=0;self.jump_request=False;self.action_request=False;self.tongue=None
        self.net=None;self.inbox=queue.Queue();self.myid=None;self.room='';self.notice='';self.started=False
        self.view=CroakView(self,size_hint=(1,1));self.add_widget(self.view)
        self.hud=Label(text='',size_hint=(.6,.08),pos_hint={'x':.2,'top':1},color=(.3,.2,.25,1),bold=True)
        self.add_widget(self.hud)
        self.layer=FloatLayout(size_hint=(1,1));self.add_widget(self.layer)
        self._load_progress();self.show_menu();Clock.schedule_interval(self.update,1/60)

    def _load_progress(self):
        self.savefile=os.path.join(App.get_running_app().user_data_dir if App.get_running_app() else BASE,'progress.json')
        try:self.unlocked=max(1,min(9,int(json.load(open(self.savefile)).get('unlocked',1))))
        except Exception:self.unlocked=1
    def save_progress(self):
        try:
            with open(self.savefile,'w') as f:json.dump({'unlocked':self.unlocked},f)
        except OSError:pass
    def clear_ui(self):self.layer.clear_widgets()
    def btn(self,label,x,y,w,h,callback):
        b=Button(text=label,size_hint=(w,h),pos_hint={'x':x,'y':y},background_color=(.74,.45,.57,1),font_size='17sp')
        b.bind(on_release=lambda *_:callback());self.layer.add_widget(b);return b
    def show_menu(self):
        self.mode='menu';self.net_close();self.clear_ui();self.hud.text='CROAK SQUAD — Android preview'
        self.btn('OFFLINE / CHỌN MÀN',.22,.74,.56,.09,self.show_levels)
        self.ip=TextInput(text='127.0.0.1',multiline=False,size_hint=(.56,.075),pos_hint={'x':.22,'y':.60})
        self.layer.add_widget(self.ip)
        self.code=TextInput(hint_text='Mã phòng (VD: ABC12)',multiline=False,size_hint=(.56,.075),pos_hint={'x':.22,'y':.50})
        self.layer.add_widget(self.code)
        self.btn('TẠO PHÒNG',.22,.37,.26,.10,lambda:self.connect(True))
        self.btn('VÀO PHÒNG',.52,.37,.26,.10,lambda:self.connect(False))
        self.msg=Label(text=self.notice,size_hint=(.9,.15),pos_hint={'x':.05,'y':.14},color=(.35,.2,.3,1));self.layer.add_widget(self.msg)
    def show_levels(self):
        self.mode='levels';self.clear_ui();self.hud.text='CHỌN MÀN — mở khóa sau khi qua màn'
        for i in range(9):
            r,c=divmod(i,3)
            self.btn(f'MÀN {i+1}'+('  🔒' if i>=self.unlocked else ''),.15+c*.25,.65-r*.17,.21,.115,(lambda j=i:self.begin(j)) if i<self.unlocked else lambda:None)
        self.btn('QUAY LẠI',.36,.06,.28,.09,self.show_menu)
    def begin(self,stage=0,online=False):
        self.mode='play';self.stage=stage;self.elapsed=0;self.cp=0;self.camera=0;self.active=self.myid if online else 'p1'
        if online:
            self.players.setdefault(self.myid,self.player(100,480,0))
        else:
            self.players={'p1':self.player(100,480,0),'p2':self.player(175,480,2)}
        self.setup_controls();self.hud.text=f'MÀN {stage+1}/9 — CHECKPOINT 0'
    def player(self,x,y,color):return dict(x=float(x),y=float(y),vx=0.,vy=0.,ground=False,coyote=0.,buffer=0.,face=1,color=color,holding=None,heldby=None,pending=None,pending_timer=0.,launch=0.)
    def setup_controls(self):
        self.clear_ui()
        self.btn('◀',.02,.035,.14,.17,lambda:None);self.btn('▶',.18,.035,.14,.17,lambda:None)
        self.btn('NHẢY',.67,.035,.14,.17,self.jump)
        self.btn('HÚT / BẮN',.82,.035,.16,.17,self.action)
        if self.net is None:self.btn('ĐỔI P1/P2',.35,.035,.25,.10,self.swap)
        self.btn('MENU',.01,.89,.12,.08,self.show_menu)
        # Track button press and release for continuous walking.
        for child in self.layer.children:
            if isinstance(child,Button) and child.text in ('◀','▶'):
                sign=-1 if child.text=='◀' else 1
                child.bind(state=lambda obj,value,s=sign:self._hold(s,value))
    def _hold(self,sign,value):
        if value=='down':self.axis=sign
        elif self.axis==sign:self.axis=0
    def swap(self):self.active='p2' if self.active=='p1' else 'p1'
    def jump(self):self.jump_request=True
    def action(self):self.action_request=True
    def net_close(self):
        old=self.net;self.net=None
        if old:
            try:old.close()
            except OSError:pass
    def connect(self,create):
        if not create and not self.code.text.strip():self.msg.text='Vui lòng nhập mã phòng';return
        host=self.ip.text.strip() or '127.0.0.1';room=self.code.text.strip().upper()
        self.msg.text='Đang kết nối...'
        def worker():
            try:
                sk=socket.create_connection((host,5056),timeout=5)
                sk.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1);sk.settimeout(None)
                sk.sendall((json.dumps({'mode':'create' if create else 'join','name':'Android','color':0,'room':room})+'\n').encode())
                self.inbox.put(('socket',sk))
                for line in sk.makefile('r',encoding='utf-8'):
                    try:self.inbox.put(('packet',json.loads(line)))
                    except ValueError:pass
                self.inbox.put(('closed',None))
            except Exception as ex:self.inbox.put(('error',str(ex)))
        threading.Thread(target=worker,daemon=True).start()
    def send(self,obj):
        if self.net:
            try:self.net.sendall((json.dumps(obj)+'\n').encode())
            except OSError:self.notice='Mất kết nối máy chủ'
    def read_network(self):
        while not self.inbox.empty():
            typ,msg=self.inbox.get_nowait()
            if typ=='socket':self.net=msg
            elif typ=='error':self.notice='Kết nối lỗi: '+msg;self.show_menu()
            elif typ=='closed':
                if self.net:self.notice='Server đã ngắt kết nối';self.show_menu()
            elif typ=='packet':
                k=msg.get('type')
                if k=='error':self.notice=msg.get('message','Lỗi phòng');self.net_close();self.show_menu()
                elif k=='welcome':
                    self.myid=msg['id'];self.room=msg['room'];self.stage=msg.get('stage',0);self.mode='lobby';self.clear_ui()
                    self.hud.text='PHÒNG: '+self.room
                    self.btn('BẮT ĐẦU',.36,.4,.28,.13,lambda:self.send({'type':'start'}))
                    self.btn('MENU',.02,.86,.14,.1,self.show_menu)
                    if msg.get('started'):self.begin(self.stage,online=True)
                elif k=='roster':
                    new={}
                    for pid,p in msg.get('players',{}).items():
                        old=self.players.get(pid,self.player(p.get('x',100),p.get('y',480),p.get('color',0)))
                        old.update(color=p.get('color',0),heldby=p.get('heldby'),holding=p.get('held'))
                        if pid!=self.myid:old.update(x=p.get('x',100),y=p.get('y',480),face=p.get('face',1))
                        new[pid]=old
                    self.players=new
                elif k=='start':self.begin(self.stage,online=True)
                elif k=='stage':self.begin(msg.get('stage',0),online=True)
                elif k=='state' and msg.get('id')!=self.myid:
                    p=self.players.get(msg['id']);
                    if p:p.update(x=msg.get('x',p['x']),y=msg.get('y',p['y']),face=msg.get('face',1))
                elif k=='grab':
                    p=self.players.get(msg['id']);target=self.players.get(msg['target'])
                    if p and target:p['holding']=msg['target'];target['heldby']=msg['id']
                elif k=='action' and msg.get('action')=='suck':
                    a=self.players.get(msg.get('id'));b=self.players.get(msg.get('target'))
                    if a and b:self.tongue=(msg['id'],b['x'],b['y'],time.monotonic()+.46)
                elif k=='throw':
                    a=self.players.get(msg.get('id'));b=self.players.get(msg.get('target'))
                    if a and b:
                        a['holding']=None;b['heldby']=None;b.update(x=a['x']+a['face']*50,y=a['y']-40,vx=msg['vx'],vy=msg['vy'],launch=.48)
    def do_action(self):
        p=self.players.get(self.active)
        if not p or p['heldby'] or p['pending']:return
        if p['holding']:
            if self.net:self.send({'type':'throw'});return
            other=self.players[p['holding']];other.update(x=p['x']+p['face']*52,y=p['y']-30,vx=p['face']*300,vy=-300,launch=.48,heldby=None)
            p['holding']=None;return
        candidates=[(abs(v['x']-p['x']),k) for k,v in self.players.items() if k!=self.active and not v['heldby'] and abs(v['x']-p['x'])<=REACH and abs(v['y']-p['y'])<=100]
        target=min(candidates)[1] if candidates else None
        tx=self.players[target]['x'] if target else p['x']+p['face']*REACH
        ty=self.players[target]['y'] if target else p['y']
        self.tongue=(self.active,tx,ty,time.monotonic()+.46)
        if target:
            if self.net:self.send({'type':'grab','target':target})
            else:p['pending']=target;p['pending_timer']=.46
    def respawn(self,pid):
        p=self.players[pid];x,y=maps.LEVELS[self.stage]['checkpoints'][self.cp]
        p.update(x=x+(22 if pid!='p1' else -22),y=y,vx=0.,vy=0.,ground=False,coyote=0.,buffer=0.,launch=0.,pending=None)
        if p['holding'] in self.players:self.players[p['holding']]['heldby']=None
        p['holding']=None
    def update(self,dt):
        dt=min(dt,.033);self.read_network()
        if self.mode!='play':return
        self.elapsed+=dt
        if self.active not in self.players:return
        if self.jump_request:self.players[self.active]['buffer']=.13
        if self.action_request:self.do_action()
        self.jump_request=False;self.action_request=False
        lvl=maps.LEVELS[self.stage];blocks=maps.solids(self.stage,self.elapsed)
        for pid,p in list(self.players.items()):
            if p['pending']:
                p['pending_timer']-=dt
                if p['pending_timer']<=0:
                    target=p['pending'];p['pending']=None;p['holding']=target;self.players[target]['heldby']=pid
            if p['heldby']:
                holder=self.players.get(p['heldby'])
                if holder:p.update(x=holder['x'],y=holder['y']-50,vx=0,vy=0)
                continue
            if any(q['pending']==pid for q in self.players.values()):continue
            # Online remote positions are server replicated, not simulated twice.
            if self.net and pid!=self.active:continue
            axis=self.axis if pid==self.active else 0
            if axis:p['face']=axis
            p['buffer']=max(0,p['buffer']-dt)
            p['coyote']=.10 if p['ground'] else max(0,p['coyote']-dt)
            if p['launch']>0:p['launch']=max(0,p['launch']-dt)
            else:p['vx']=axis*172
            if p['buffer']>0 and p['coyote']>0:
                p['vy']=-335;p['ground']=False;p['coyote']=p['buffer']=0
            p['vy']=min(820,p['vy']+1150*dt)
            xx=p['x']+p['vx']*dt;yy=p['y']
            for b in blocks:
                if rect_hit((xx-22,yy-25,44,52),b):
                    if p['vx']>0:xx=b[0]-22
                    elif p['vx']<0:xx=b[0]+b[2]+22
                    p['vx']=0
            yy+=p['vy']*dt;p['ground']=False
            for b in blocks:
                if rect_hit((xx-22,yy-25,44,52),b):
                    if p['vy']>0:yy=b[1]-27;p['ground']=True
                    elif p['vy']<0:yy=b[1]+b[3]+25
                    p['vy']=0
            if p['ground'] and p['buffer']>0:
                p['vy']=-335;p['ground']=False;p['buffer']=0
            p.update(x=max(30,min(lvl['width']-30,xx)),y=yy)
            if p['ground']:
                for idx,(cx,cy) in enumerate(lvl['checkpoints']):
                    if p['x']>=cx and abs(p['y']-562)<90:self.cp=max(self.cp,idx)
            if yy>750 or maps.deadly(self.stage,self.elapsed,(p['x']-22,yy-25,44,52)):self.respawn(pid)
            if p['x']>=lvl['goal'] and abs(p['y']-550)<150:
                if self.net:
                    self.send({'type':'next'});p['x']=lvl['goal']-60
                elif self.stage<8:
                    self.unlocked=max(self.unlocked,self.stage+2);self.save_progress();self.begin(self.stage+1)
                else:
                    self.notice='Đã hoàn thành 9 màn!';self.show_menu()
                break
        self.camera+=(max(0,min(lvl['width']-GW,self.players[self.active]['x']-GW*.42))-self.camera)*min(1,dt*8)
        self.hud.text=f'MÀN {self.stage+1}/9  |  CHECKPOINT {self.cp}  |  {self.active if not self.net else self.room}'
        self.view.paint()
        if self.net:
            self._last_net=getattr(self,'_last_net',0)+dt
            if self._last_net>.05:
                p=self.players[self.active];self.send({'type':'state','x':p['x'],'y':p['y'],'face':p['face']});self._last_net=0

class CroakApp(App):
    def build(self):
        self.title='Croak Squad Android Preview'
        if platform!='android':Window.size=(1100,680)
        return CroakRoot()

if __name__=='__main__':CroakApp().run()
