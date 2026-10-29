"""V17 level definitions, extracted without Pygame dependency."""
import math
GROUND_Y=590
SECTION_LENGTH=800
TOTAL_LEVELS=9
def build_level(level_id):
    # Nine authored stage recipes: first learn, then combine, then master.
    # Every section starts with a generous flat and safe approach.
    tier=level_id//3
    count=7+tier+(level_id%3)
    gaps=[];blocks=[];spikes=[];moving=[];saws=[];crushers=[];orbs=[]
    checkpoints=[(100.,450.)]
    # Only one to three obstacles between checkpoints; place flags on flat ground.
    recipes=[
      ['gap','steps','gap','island','steps','moving','gap'],
      ['gap','island','steps','moving','gap','island','moving','gap'],
      ['steps','gap','moving','island','moving','gap','saw','island','moving'],
      ['gap','island','moving','steps','saw','gap','moving','island'],
      ['steps','moving','saw','island','crusher','moving','gap','saw','island'],
      ['island','saw','moving','crusher','island','spikes','moving','saw','gap','crusher'],
      ['moving','saw','spikes','island','crusher','moving','orb','gap','saw'],
      ['saw','moving','crusher','orb','spikes','island','moving','orb','crusher','gap'],
      ['moving','orb','crusher','spikes','saw','island','orb','moving','crusher','spikes','gap'],
    ][level_id]
    for i,kind in enumerate(recipes):
        base=i*SECTION_LENGTH
        if i>0 and i%3==0:checkpoints.append((base+110.,450.))
        if kind=='gap':
            gap_width=70+min(95,tier*32+(i%2)*22)
            gaps.append((base+430,base+430+gap_width))
        elif kind=='steps':
            blocks.extend([(base+295,558,122,18),(base+445,530,112,18),(base+580,504,105,18)])
        elif kind=='island':
            gw=155+min(60,tier*18)
            gaps.append((base+390,base+390+gw))
            blocks.append((base+424,535,92,18))
        elif kind=='moving':
            gaps.append((base+385,base+570+tier*12))
            blocks.append((base+435,542,78,17))
            moving.append((base+435,520,96,30+tier*8,0,4.6-tier*.3,.13*level_id))
        elif kind=='saw':
            # Clearly telegraphed single patrolling saw on safe floor.
            saws.append((base+525,554,55+tier*17,0,4.4-tier*.3,.15*i,22+tier*2))
        elif kind=='crusher':
            crushers.append((base+535,315,85,54,190,5.0-tier*.3,.13*i))
        elif kind=='spikes':
            spikes.append((base+495,550,72+tier*12))
            blocks.append((base+460,532,110,18))
        elif kind=='orb':
            # Moving orb at midair height: jump underneath or time your launch.
            orbs.append((base+535,500,60,35,4.1-tier*.25,.2*i,19+tier*3))
    width=len(recipes)*SECTION_LENGTH+290
    checkpoints.append((len(recipes)*SECTION_LENGTH+70.,450.))
    return ({'width':width,'ground':GROUND_Y,'blocks':blocks,'spikes':spikes,
             'goal':width-135,'checkpoints':checkpoints},
            {'gaps':gaps,'platforms':moving,'saws':saws,'crushers':crushers,'orbs':orbs})


LEVELS=[]
DYNAMIC_LEVELS=[]
for i in range(TOTAL_LEVELS):
    level,dynamic=build_level(i)
    LEVELS.append(level)
    DYNAMIC_LEVELS.append(dynamic)

def motion(t,period,phase):
    return math.sin((t+phase)*math.tau/period)

def moving_objects(stage,t):
    d=DYNAMIC_LEVELS[stage]
    platforms=[(x+dx*motion(t,period,phase), y+dy*motion(t,period,phase),w,17) for x,y,w,dx,dy,period,phase in d['platforms']]
    saws=[(x+dx*motion(t,period,phase),y+dy*motion(t,period,phase),r) for x,y,dx,dy,period,phase,r in d['saws']+d.get('orbs',[])]
    crushers=[(x,y+dy*(1+motion(t,period,phase))/2,w,h) for x,y,w,h,dy,period,phase in d['crushers']]
    return platforms,saws,crushers

def solids(stage,t):
    lvl=LEVELS[stage];out=list(lvl['blocks']);edge=0
    for left,right in DYNAMIC_LEVELS[stage]['gaps']:
        if left>edge:out.append((edge,590,left-edge,120))
        edge=right
    if edge<lvl['width']:out.append((edge,590,lvl['width']-edge,120))
    return out+moving_objects(stage,t)[0]

def intersects(a,b):
    x,y,w,h=a; xx,yy,ww,hh=b
    return x<xx+ww and x+w>xx and y<yy+hh and y+h>yy

def deadly(stage,t,rect):
    platforms,saws,crushers=moving_objects(stage,t)
    for x,y,r in saws:
        rx=max(rect[0],min(x,rect[0]+rect[2]));ry=max(rect[1],min(y,rect[1]+rect[3]))
        if (rx-x)**2+(ry-y)**2<(r-3)**2:return True
    if any(intersects(rect,c) for c in crushers):return True
    return any(intersects(rect,(x,y,w,40)) for x,y,w in LEVELS[stage]['spikes'])
