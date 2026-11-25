"""v4 continuous controller: construction, input, simulation and progression."""

from __future__ import annotations

import math
from dataclasses import replace

import pygame

from .. import config
from ..baseline_game import EVENT_SOUNDS, Game as PrototypeGame
from ..boss import AlzheimerBoss
from ..continuum import REGIONS, WORLD_WIDTH, ContinuousWorld, region_at
from ..encounters import EncounterDirector
from ..engine import DT
from ..light import LivingLantern
from ..physics import NurInput
from ..refuges import INWARD, RefugeBook
from ..sanity import HallucinationAudio, HallucinationVisuals, PhantomDirector, SanityManager
from ..soundscape import Soundscape
from ..state import Memory, Stamina
from ..story import FRAGMENTS
from ..vistas import Vistas
from ..wisp import WispAnimation
from .finale import LocalFinale
from .persistence import PersistenceMixin
from .presentation import PresentationMixin


class Game(PersistenceMixin, PresentationMixin, PrototypeGame):
    def __init__(self,*args,**kwargs):
        if not pygame.get_init():
            pygame.mixer.pre_init(22050,-16,2,512)
        self.refuges=RefugeBook()
        self.planted=None
        self.interaction_held=False
        self.phase_held=False
        self.last_refuge=0
        self.inward_timer=16.
        self.transitions=0
        super().__init__(*args,**kwargs)
        self.audio.close()
        self.audio=Soundscape(enabled=not self.muted)
        self.art=Vistas(config.SIZE,seed=self.seed)
        self.lantern=LivingLantern()
        self.sanity=SanityManager()
        self.phantoms=PhantomDirector(seed=self.seed)
        self.hallucination_visuals=HallucinationVisuals(seed=self.seed)
        self.hallucination_audio=HallucinationAudio()
        self.camera=max(0,self.world.player.position.x-config.SIZE[0]*.42)
        self.last_refuge=self.room
        self._say("E · stasiun sumbu. A/D berjalan · Shift lari · Q gaung · H halusinasi · J peta.",8)

    def _build_world(self,room):
        world=ContinuousWorld(room,self.quest_progress)
        world.stamina=self.stamina
        q=world.quest
        if q and q.stage:
            n=q.plan.nodes[q.plan.order[q.stage-1]]
            world.player.position=(n.x,n.y)
        return world

    def _build_threats(self,room):
        return EncounterDirector()

    def _build_boss(self,room):
        return LocalFinale(self.seed+17*room)

    def start(self,room=None,seed=None):
        super().start(room,seed)
        self.lantern=LivingLantern()
        self.refuges=RefugeBook()
        self.sanity=SanityManager()
        self.phantoms=PhantomDirector(seed=self.seed)
        self.hallucination_visuals=HallucinationVisuals(seed=self.seed)
        self.hallucination_audio=HallucinationAudio()
        self.planted=None
        self.last_refuge=self.room
        self.camera=max(0,self.world.player.position.x-config.SIZE[0]*.42)
        self.transitions=0
        self.interaction_held=self.plant_held=self.free_shift_held=False
        self.phase_held=False
        self.inward_timer=16.
        self._save()

    def _remember_quest(self):
        self.quest_progress=self.world.progress()

    def restart_room(self,keep_boss=False):
        # Retry is an intentional checkpoint move inside the SAME physics world.
        r=REGIONS[self.last_refuge]
        self.world._release()
        self.world.player.position=r.refuge
        self.world.player.velocity=(0,0)
        self.world.hazards.reset_near(r.refuge[0])
        self.world.space.reindex_shapes_for_body(self.world.player)
        self.world.dead=False
        self.world.death_reason=""
        self.sanity.reset()
        self.phantoms.clear()
        self.world.grounded=False
        self.world.support=None
        self.world.gliding=self.world.sprinting=False
        self.world.jump_buffer=self.world.coyote=0
        self.death_timer=0
        self.state='playing'
        self.room=r.index
        self.world.chapter=self.room
        self.world.quest=self.world.quests.get(self.room)
        self.player_animation=WispAnimation()
        self.planted=None
        self.lantern.carried=True
        self.lantern.focus=False
        self.pending_action=self.pending_shift=False
        self.interaction_held=self.plant_held=self.free_shift_held=False
        self.phase_held=False
        self.accumulator=0
        self.camera=max(0,r.refuge[0]-config.SIZE[0]*.42)

    def _control(self):
        control=super()._control()
        keys=pygame.key.get_pressed()
        return replace(control,focus=bool(keys[pygame.K_f]))

    def event(self,event):
        if event.type==pygame.KEYDOWN:
            if event.key==pygame.K_g and self.state=='playing':
                self._plant()
                return
            if event.key==pygame.K_h and self.state=='playing':
                self.sanity.trigger_hallucination()
                return
            if self.lantern.charge<=0 and event.key==pygame.K_e and self.state=='playing':
                self._recover_darkness()
                return
        super().event(event)

    @property
    def light_origin(self):
        return self.planted if self.planted is not None else self._player_xy()

    def _plant(self):
        if self.planted is None:
            self.planted=self._player_xy()
            self.lantern.carried=False
            self.lantern.focus=False
            self._say("Lentera tinggal di sini. G dekat lentera untuk mengambil. Di luar cahayanya, bayangan bisa menyentuhmu.",5)
        elif math.dist(self.planted,self._player_xy())<80:
            self.planted=None
            self.lantern.carried=True
        else:
            self._say("Kembali ke lentera dahulu · J untuk melihat letaknya.",3)

    def _recover_darkness(self):
        self.lantern.recover()
        self.restart_room()
        self._say("Bara cadangan di stasiun terakhir. Jejak yang sudah diikat tidak hilang.",7)
        self._save()

    def _care(self,control):
        edge=control.action and not self.interaction_held
        self.interaction_held=bool(control.action)
        if not edge:
            return False
        r=REGIONS[self.room]
        px,py=self._player_xy()
        if math.dist((px,py),r.refuge)<75:
            self.last_refuge=r.index
            kindled=self.lantern.kindle(f"refuge:{r.index}")
            if kindled:
                self.stamina.amount=max(.8,self.stamina.amount)
                self.stamina.exhausted=False
                self.stamina.recovery_delay=0
                self.sanity.restore_sanity(20)
            self.world.glide_unlocked=True
            self.refuges.visited.add(r.index)
            available=self.refuges.threads-self.refuges.delivered
            if available:
                thread=min(available)
                self.refuges.delivered.add(thread)
                self.lantern.kindle(f"thread:{thread}")
                text="PITA DISIMPAN · satu cadangan bara ditambahkan. Stasiun ini menjadi tanda perjalanan balik."
            elif kindled:
                text="STASIUN SUMBU · satu bara, napas, dan ketenangan baru. Tahan lompat saat turun untuk melayang; napas berkurang."
            else:
                text="SUMBU SUDAH DIRAWAT · cahaya stasiun ini telah dipakai. Bawa pita ke stasiun berikutnya."
            self.journal[f"care:{r.index}"]=text
            self._say(text,5)
            self.audio.play('memory',.4)
            self._save()
            return True
        for region in REGIONS[:-1]:
            x=region.start+region.source.level.width+365
            if abs(px-x)<45 and abs(py-328)<42 and region.index not in self.refuges.threads:
                self.refuges.threads.add(region.index)
                self.journal[f"thread:{region.index}"]="Pita ditemukan di tempat tinggi. Simpan di stasiun sumbu berikutnya."
                self._say("PITA INGATAN · simpan di stasiun sumbu berikutnya.",5)
                return True
        return False

    def update(self,dt,control=None):
        dt=min(.1,max(0,dt))
        self.visual_time+=dt
        self.notice_timer=max(0,self.notice_timer-dt)
        self.audio.update(dt,self.lantern.band,self.lantern.illumination,
                          boss=self.boss is not None and self.boss.phase>=1,
                          phase=self.world.phase,ending=self.state=='ending')
        if self.state=='ending':
            self.cutscene_timer+=dt
            if self.cutscene_timer>4.6:
                self.cutscene_index=min(7,self.cutscene_index+1)
                self.cutscene_timer=0
            return
        if self.state!='playing':
            return
        control=control or self._control()
        if self.lantern.charge<=0:
            if control.action:
                self._recover_darkness()
            return
        self.play_seconds+=dt
        self.lantern.focus=bool(getattr(control,'focus',False) and self.lantern.carried)
        self.lantern.step(dt)
        if self.lantern.charge<=0:
            return
        if self.sanity.update(dt,self.lantern) and not self.world.dead:
            self.world.kill("Akalmu kehabisan tempat untuk berdiri. Cahaya pun tidak menemukan jalan pulang.")
        self.hallucination_audio.apply(self.audio,self.sanity.intensity)
        self.phantoms.update(dt,self.sanity.current_sanity,self.sanity.max_sanity,self._player_xy())
        if getattr(control,'plant',False) and not getattr(self,'plant_held',False):
            self._plant()
        self.plant_held=getattr(control,'plant',False)
        if self._care(control):
            return
        shift_edge=bool(getattr(control,'shift',False)) and not self.phase_held
        self.phase_held=bool(getattr(control,'shift',False))
        self.accumulator=min(.1,self.accumulator+dt)
        while self.accumulator>=DT:
            self.world.step(control,DT)
            self.accumulator-=DT
            for event in self.world.drain_events():
                if event in EVENT_SOUNDS:
                    self.audio.play(EVENT_SOUNDS[event],.4)
            if self.world.dead:
                break
        r=region_at(self.world.player.position.x)
        if r.index!=self.room:
            self.room=r.index
            self.world.chapter=self.room
            self.world.quest=self.world.quests.get(self.room)
            self.transitions+=1
            self._say(r.source.name+" · jalan tetap terbuka di belakangmu",4)
            if self.room==config.BOSS_ARENA_ROOM and self.boss is None:
                self.boss=self._build_boss(self.room)
            self._save()
        if math.dist(self._player_xy(),r.refuge)<75:
            self.last_refuge=r.index
        self.player_animation.update(dt,self.world.player.velocity,self.world.grounded,self.world.sprinting)
        pose='glide' if self.world.gliding else 'focus' if self.lantern.focus and abs(self.world.player.velocity.x)<12 else None
        if pose:
            self.player_animation.pose=pose
            self.player_animation.frame=int(self.visual_time*(10 if pose=='glide' else 8))%8
        if self.world.quest:
            self.world.quest.shift_held=False
            quest_control=replace(control,shift=shift_edge) if isinstance(control,NurInput) else control
            result=self.world.quest.update(quest_control,self.world,dt)
            self.world.set_phase(self.world.quest.phase)
            if result:
                self._say(result['text'],5)
                if result.get('shifted'):
                    self.audio.play('breath',.25)
                if result.get('journal'):
                    self.journal[f"{self.room:02d}:{result['index']}"]=result['journal']
                if result.get('solved'):
                    self.lantern.milestone(sum(q.stage for q in self.world.quests.values()))
                    self.audio.play('memory',.45)
                    self._save()
        elif shift_edge:
            self.world.set_phase(1-self.world.phase)
        self.free_shift_held=bool(getattr(control,'shift',False))
        px,py=self._player_xy()
        for f in FRAGMENTS:
            if f.room==self.room and f.key not in self.memory.found and math.dist((px,py),(f.x+r.start,f.y))<36:
                self.memory.add(f.key,false=False)
                self.lantern.collect_fragment()
                self.journal[f"memory:{f.key}"]=f.true_text
                self._say(f.true_text,5)
                self.audio.play('memory',.5)
        if self.threats.update(dt,(px,py),self.lantern,self.light_origin,elapsed=self.play_seconds,world=self.world) and not self.world.dead:
            self.world.kill("Bayangan menyentuhmu di luar cahaya lentera yang ditinggalkan.")
        self.inward_timer-=dt
        if self.inward_timer<=0:
            self.inward_timer=(24,18,12,8)[self.lantern.band]
            if self.notice_timer<=0:
                self._say("NUR · DALAM HATI: "+INWARD[self.lantern.band],5)
        if self.boss is not None and self.room==config.BOSS_ARENA_ROOM and not self.world.dead:
            self._handle_boss_event(self.boss.update(dt,(px,py),control.action,self.lantern.illumination,self.lantern.protects))
        if self.world.dead:
            self.death_timer+=dt
            if self.death_timer>1.05:
                self.lantern.die()
                self.restart_room()
            return
        target=max(0,min(WORLD_WIDTH-config.SIZE[0],px-config.SIZE[0]*.42))
        self.camera+=(target-self.camera)*min(1,dt*4)


