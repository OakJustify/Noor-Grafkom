"""Version-4 checkpoint writing, validation and loading."""

from __future__ import annotations

import json
import math

from .. import config
from ..continuum import REGIONS, WORLD_WIDTH, ContinuousWorld, region_at
from ..encounters import EncounterDirector
from ..light import LivingLantern
from ..refuges import RefugeBook
from ..sanity import HallucinationAudio, PhantomDirector, SanityManager
from ..state import Memory, Stamina
from ..story import FRAGMENTS
from ..wisp import WispAnimation


class PersistenceMixin:
    def _save(self):
        if not self.persist or not isinstance(self.lantern,LivingLantern):
            return
        data={"version":4,"seed":self.seed,"room":self.room,"position":list(self._player_xy()),
              "quests":self.world.progress(),"lantern":self.lantern.snapshot(),
              "stamina":self.stamina.snapshot(),"refuges":self.refuges.snapshot(),
              "journal":self.journal,"last_refuge":self.last_refuge,"play_seconds":self.play_seconds,
              "phase":self.world.phase,"glide":self.world.glide_unlocked,
              "bestiary_seen":sorted(self.threats.unlocked),
              "memory":self.memory.snapshot(),"planted":self.planted,"sanity":self.sanity.snapshot(),
              "finale":{**self.boss.snapshot(),"taken":[n for n,e in enumerate(self.boss.echoes) if e['taken']]} if self.boss else None,
              "props":[{"position":list(c.body.position),"velocity":list(c.body.velocity),"angle":c.body.angle}
                       for c in self.world.crates],
              "open_paths":[i for i,g in self.world.gates.items() if g['open']]}
        try:
            config.SAVE_PATH.parent.mkdir(parents=True,exist_ok=True)
            temp=config.SAVE_PATH.with_suffix('.tmp')
            temp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
            temp.replace(config.SAVE_PATH)
        except OSError:
            pass

    def load_save(self):
        try:
            saved=json.loads(config.SAVE_PATH.read_text(encoding='utf-8'))
            if saved.get('version')!=4:
                return False
            seed=int(saved['seed'])
            x,y=map(float,saved['position'])
            if not all(math.isfinite(n) for n in (x,y)) or not 0<=x<=WORLD_WIDTH or not -100<=y<=580:
                return False
            stamina=Stamina.restore(saved['stamina'])
            light=saved['lantern']
            cap,charge=float(light['capacity']),float(light['charge'])
            if not 0<=charge<=cap<=1:
                return False
            counts={key:light.get(key,0) for key in ('collections','deaths','recoveries')}
            if not all(type(n) is int and n>=0 for n in counts.values()):
                return False
            quests=saved['quests']
            if not isinstance(quests,dict):
                return False
            for key,q in quests.items():
                if not key.isdigit() or int(key) not in range(4,28) or not isinstance(q,dict):
                    return False
                if not isinstance(q.get('stage'),int) or not 0<=q['stage']<=6 or q.get('phase') not in (0,1):
                    return False
                if not isinstance(q.get('inspected',[]),list) or not all(type(n) is int and 0<=n<6 for n in q.get('inspected',[])):
                    return False
            book=saved.get('refuges')
            if book is None:
                # Retain prior v4 ribbon inventory; removed NPC state is ignored.
                old=saved.get('companions',{})
                book={'visited':[], 'threads':old.get('threads',[]), 'delivered':old.get('delivered',[])}
            visited=set(book['visited'])
            if not visited<=set(range(29)):
                return False
            threads=set(book['threads']); delivered=set(book['delivered'])
            if not threads<=set(range(28)) or not delivered<=threads:
                return False
            refuge=int(saved['last_refuge'])
            if not 0<=refuge<29 or not isinstance(saved['journal'],dict) or not all(isinstance(v,str) for v in saved['journal'].values()):
                return False
            seconds=float(saved['play_seconds'])
            if not math.isfinite(seconds) or seconds<0 or saved['phase'] not in (0,1):
                return False
            seen=saved.get('bestiary_seen',[])
            if not isinstance(seen,list) or not all(type(n) is int and 0<=n<8 for n in seen):
                return False
            used=light.get('refuges_used',[])
            if not isinstance(used,list) or not all(isinstance(s,str) for s in used):
                return False
            planted=saved.get('planted')
            if planted is not None and (not isinstance(planted,list) or len(planted)!=2 or
                 not all(isinstance(n,(int,float)) and math.isfinite(n) for n in planted) or not 0<=planted[0]<=WORLD_WIDTH or not -100<=planted[1]<=580):
                return False
            paths=saved.get('open_paths',[])
            if not isinstance(paths,list) or len(set(paths))!=len(paths) or not all(isinstance(i,int) and (i==2 or 4<=i<28) for i in paths):
                return False
            finale=saved.get('finale')
            if finale is not None and (not isinstance(finale,dict) or
                type(finale.get('phase')) is not int or not 0<=finale['phase']<=2 or
                type(finale.get('echoes')) is not int or not 0<=finale['echoes']<=3 or
                type(finale.get('presses')) is not int or not 0<=finale['presses']<=3 or
                not isinstance(finale.get('done'),bool)):
                return False
            if finale is not None and (not isinstance(finale.get('taken'),list) or
                not all(type(n) is int and 0<=n<3 for n in finale['taken']) or
                len(set(finale['taken']))!=finale['echoes']):
                return False
            found=saved.get('memory',{}).get('found',[])
            if not isinstance(found,list) or not set(found)<={f.key for f in FRAGMENTS}:
                return False
            props=saved.get('props',[])
            if not isinstance(props,list) or len(props) not in (0,2):
                return False
            for prop in props:
                pos=prop['position']; vel=prop['velocity']; angle=prop['angle']
                if len(pos)!=2 or len(vel)!=2 or not all(isinstance(n,(int,float)) and math.isfinite(n) for n in (*pos,*vel,angle)):
                    return False
                if not -100<=pos[0]<=WORLD_WIDTH+100 or not -500<=pos[1]<=1500:
                    return False
            sanity_saved=saved.get('sanity')
            if sanity_saved is not None:
                if not isinstance(sanity_saved,dict):
                    return False
                sanity_max=float(sanity_saved.get('max',100.0))
                sanity_current=float(sanity_saved.get('current',sanity_max))
                sanity_count=sanity_saved.get('count',0)
                sanity_hallucinating=sanity_saved.get('hallucinating',False)
                if (not math.isfinite(sanity_max) or not math.isfinite(sanity_current)
                        or not 0<sanity_max<=1000 or not 0<=sanity_current<=sanity_max
                        or type(sanity_count) is not int or sanity_count<0
                        or not isinstance(sanity_hallucinating,bool)
                        or not isinstance(sanity_saved.get('dead',False),bool)):
                    return False
            world=ContinuousWorld(region_at(x).index,quests)
        except (OSError,ValueError,TypeError,KeyError,AttributeError,OverflowError):
            return False
        self.seed=seed
        self.art.set_seed(seed)
        self.world=world
        for crate,prop in zip(world.crates,props):
            crate.body.position=prop['position']
            crate.body.velocity=prop['velocity']
            crate.body.angle=prop['angle']
        self.stamina=stamina
        world.stamina=stamina
        world.time=seconds
        world.hazards.time=seconds
        world.player.position=(x,y)
        world.set_phase(saved['phase'])
        world.glide_unlocked=bool(saved.get('glide',False))
        for i in paths:
            g=world.gates[i]
            world.space.remove(g['pair'][1],g['pair'][0])
            g['open']=True
        self.room=region_at(x).index
        self.lantern=LivingLantern()
        self.lantern.capacity,self.lantern.charge=cap,charge
        self.lantern.refuges_used=set(used)
        self.lantern.collections=counts['collections']
        self.lantern.deaths=counts['deaths']
        self.lantern.recoveries=counts['recoveries']
        self.planted=tuple(planted) if planted else None
        self.lantern.carried=self.planted is None
        self.refuges=RefugeBook(visited=visited,threads=threads,delivered=delivered)
        self.memory=Memory()
        self.memory.found=set(found)
        if sanity_saved is not None:
            self.sanity=SanityManager(max_sanity=sanity_max,current_sanity=sanity_current,
                                      hallucination_count=sanity_count,
                                      hallucinating=sanity_hallucinating)
        else:
            self.sanity=SanityManager()
        self.sanity.update(0,self.lantern)
        self.phantoms=PhantomDirector(seed=self.seed)
        self.hallucination_audio=HallucinationAudio()
        self.last_refuge=refuge
        self.journal=saved['journal']
        self.play_seconds=seconds
        self.threats=EncounterDirector()
        self.threats.unlocked=set(seen)
        self.threats.elapsed=seconds
        self.boss=self._build_boss(28) if self.room==28 or finale else None
        if finale:
            self.boss.local.phase=finale['phase']
            self.boss.local.name_presses=finale['presses']
            for n,echo in enumerate(self.boss.echoes):
                echo['taken']=n in finale['taken']
            self.boss.local.done=finale['done']
        self.state='ending' if finale and finale['done'] else 'playing'
        self.player_animation=WispAnimation()
        self.camera=max(0,min(WORLD_WIDTH-960,x-403))
        self.accumulator=0
        self.death_timer=0
        self.pending_action=self.pending_shift=False
        self.interaction_held=self.plant_held=self.free_shift_held=False
        self.phase_held=False
        self.cutscene_index=self.cutscene_timer=0
        self.journal_page=0
        return True

    def snapshot(self):
        return {"version":4,"state":self.state,"region":self.room+1,"region_name":REGIONS[self.room].source.name,
                "world_width":WORLD_WIDTH,"transitions":self.transitions,"camera":round(self.camera,2),
                "lantern":self.lantern.snapshot(),"stamina":self.stamina.snapshot(),"sanity":self.sanity.snapshot(),
                "phantoms":self.phantoms.snapshot(),"physics":self.world.snapshot(),
                 "refuges":self.refuges.snapshot(),"threats":self.threats.snapshot(),
                "quest":self.world.quest.snapshot() if self.world.quest else None,
                "player_animation":self.player_animation.snapshot(),"play_seconds":round(self.play_seconds,3),
                "journal_entries":len(self.journal),"audio_targets":self.audio.drift_targets,
                "boss":self.boss.snapshot() if self.boss else None}

