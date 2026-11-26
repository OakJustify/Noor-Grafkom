"""v4 continuous controller: construction, input, simulation and progression."""

from __future__ import annotations

import math
from dataclasses import replace

import pygame

from .. import config
from ..baseline_game import EVENT_SOUNDS, Game as PrototypeGame
from ..cinematics.progress import StoryProgress
from ..cinematics.renderer import StoryRenderer
from ..cinematics.fragments import STORY_FRAGMENTS
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
        self._campaign_persist = kwargs.get('persist', True)
        self._menu_developer = False
        self.developer_mode = kwargs.pop('developer_mode', False)
        if self.developer_mode:
            kwargs['persist'] = False
        self.cinematics_enabled = kwargs.pop('cinematics', True)
        self.session_started = kwargs.get('start', True)
        self.story = StoryProgress()
        self.cinema = StoryRenderer(config.SIZE)
        self.gallery_page = 0
        self.gallery_return = 'playing'
        self.ending_page = 0
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
        self._say("E · stasiun sumbu. A/D berjalan · Shift lari · Q gaung · H ilusi · J peta · K fragmen.",8)
        if self.cinematics_enabled and self.state == 'playing' and self.room == 0:
            self.story.begin_opening()
            self.state = 'cutscene'
        elif self.state == 'playing':
            self.story.seen.add('CS00')

    def _build_world(self,room) -> ContinuousWorld:
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
        # Keep the old adapter solely for baseline mechanic regressions.
        if self.cinematics_enabled:
            return None
        return LocalFinale(self.seed+17*room)

    def start(self,room=None,seed=None):
        self.session_started = True
        self.story = StoryProgress()
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
        self.gallery_page = self.ending_page = 0
        self.gallery_return = 'playing'
        if self.cinematics_enabled and self.room == 0:
            self.story.begin_opening()
            self.state = 'cutscene'
        else:
            self.story.seen.add('CS00')
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

    def start_developer_mode(self):
        """Start a fresh unsaved practice session from the ordinary menu."""
        if self.state != 'menu' or not self.cinematics_enabled:
            return False
        self.developer_mode = True
        self.persist = False
        self._menu_developer = True
        self.start(0)
        return self.developer_jump(STORY_FRAGMENTS[0].key)

    def developer_jump(self, key):
        """Practice one memory in the existing world; never grant campaign saves."""
        if not self.developer_mode or not self.cinematics_enabled:
            return False
        fragment = next((f for f in STORY_FRAGMENTS if f.key == key), None)
        if fragment is None:
            raise ValueError('Unknown developer fragment')
        previous = STORY_FRAGMENTS[:STORY_FRAGMENTS.index(fragment)]
        self.story = StoryProgress(seen={'CS00', *(f.scene for f in previous)},
                                   collected={f.key for f in previous})
        for entry in tuple(self.journal):
            if entry.startswith('fragment:'):
                del self.journal[entry]
        self.journal.update({f'fragment:{f.key}': f.title for f in previous})
        self.session_started = True
        self.last_refuge = fragment.region
        self.restart_room()
        self.world.flip_gravity(1)
        self.world.gravity_remaining = self.world.gravity_beep_remaining = 0
        self.world.set_phase(0)
        self.world.events.clear()
        self.world.action_held = False
        self.world.regrab_delay = 0
        self.world.facing = 1
        self.world.player.position = (fragment.position[0] - 90, fragment.position[1])
        self.world.space.reindex_shapes_for_body(self.world.player)
        self.lantern = LivingLantern()
        self.stamina = Stamina()
        self.world.stamina = self.stamina
        self.gallery_page = self.ending_page = 0
        self.gallery_return = 'playing'
        self.camera = max(0, min(WORLD_WIDTH-config.SIZE[0], fragment.position[0]-90-config.SIZE[0]*.42))
        self.audio.set_muted(self.muted)
        self._say(f'DEVELOPER · {fragment.key}: {fragment.title}. Jalan ke kanan untuk memicu cutscene. Save nonaktif.', 7)
        return True

    def developer_ending(self, stage='void'):
        """Preview the finale or closing cards without writing campaign progress."""
        if not self.developer_mode or not self.cinematics_enabled:
            return False
        if stage not in ('void', 'realworld', 'cards'):
            raise ValueError('Unknown developer ending stage')
        fragment = STORY_FRAGMENTS[-1]
        self.developer_jump(fragment.key)
        self.story.collect(fragment.key)
        self.journal[f'fragment:{fragment.key}'] = fragment.title
        self.story.skip()
        self.last_refuge = len(REGIONS)-1
        self.restart_room()
        self.world.player.position = (WORLD_WIDTH-140, 438)
        self.world.space.reindex_shapes_for_body(self.world.player)
        self.camera = WORLD_WIDTH-config.SIZE[0]
        self.story.request_finale()
        if stage in ('realworld', 'cards'):
            self.story.skip()
        if stage == 'cards':
            self.story.skip()
        self._sync_story_state()
        return True

    def return_to_menu(self):
        """Leave the journey for the main menu without discarding the checkpoint.

        Only a paused journey can return; the world, story and camera are left
        untouched so that C (continue) or a new start behaves exactly as it
        would after any other menu visit.
        """
        if self.state != 'paused':
            return False
        self._save()
        self.state = 'menu'
        self.session_started = False
        self.developer_mode = False
        self.persist = self._campaign_persist
        self._menu_developer = False
        self.audio.set_muted(self.muted)
        return True

    def _control(self):
        control=super()._control()
        keys=pygame.key.get_pressed()
        return replace(control,focus=bool(keys[pygame.K_f]))

    def event(self,event):
        if self.state == 'menu' and self.cinematics_enabled:
            keyboard = event.type == pygame.KEYDOWN and event.key == pygame.K_d
            click = (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                     and self._developer_button_rect().collidepoint(self._canvas_point(event.pos)))
            if keyboard or click:
                self.start_developer_mode()
                return
            if (self._menu_developer and event.type == pygame.KEYDOWN
                    and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_c)):
                self.developer_mode = False
                self.persist = self._campaign_persist
                self.session_started = False
                self._menu_developer = False
        if self.developer_mode and event.type == pygame.KEYDOWN:
            keys = (pygame.K_F1, pygame.K_F2, pygame.K_F3, pygame.K_F4, pygame.K_F5, pygame.K_F6)
            for key, fragment in zip(keys, STORY_FRAGMENTS):
                if event.key == key:
                    self.developer_jump(fragment.key)
                    return
            endings = {pygame.K_F7: 'void', pygame.K_F8: 'realworld', pygame.K_F9: 'cards'}
            if event.key in endings:
                self.developer_ending(endings[event.key])
                return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            self.muted = not self.muted
            self.audio.set_muted(self.muted or self.story.active == 'CS07')
            return
        if self.cinematics_enabled and event.type == pygame.KEYDOWN:
            if self.state == 'paused' and event.key == pygame.K_b:
                self.return_to_menu()
                return
            if self.state == 'ending':
                if event.key == pygame.K_RETURN:
                    self.ending_page = (self.ending_page+1) % 3
                elif event.key == pygame.K_r:
                    self.start(0)
                elif event.key == pygame.K_ESCAPE:
                    self._save()
                    self.state = 'menu'
                elif event.key == pygame.K_k:
                    self.gallery_return = 'ending'
                    self.gallery_page = len(self.gallery_options)-1
                    self.state = 'gallery'
                return
            if self.state == 'menu' and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start(0)
                return
            if event.key == pygame.K_k and self.state in ('playing', 'journal', 'paused', 'ending'):
                self.gallery_return = self.state
                self.gallery_page = max((i for i, (key, _) in enumerate(self.gallery_options)
                                         if key in self.story.seen), default=0)
                self.state = 'gallery'
                return
            if self.state == 'gallery':
                if event.key in (pygame.K_ESCAPE, pygame.K_k):
                    self.state = self.gallery_return
                elif event.key in (pygame.K_UP, pygame.K_LEFT):
                    self.gallery_page = (self.gallery_page-1) % len(self.gallery_options)
                elif event.key in (pygame.K_DOWN, pygame.K_RIGHT):
                    self.gallery_page = (self.gallery_page+1) % len(self.gallery_options)
                elif event.key == pygame.K_RETURN:
                    key, _ = self.gallery_options[self.gallery_page]
                    if self.story.begin_replay(key):
                        self._sync_story_state()
                return
        if self.state == 'cutscene' and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.story.skip()
                self._sync_story_state()
            elif event.key == pygame.K_SPACE:
                self.story.paused = not self.story.paused
            elif event.key == pygame.K_RETURN:
                self.story.advance()
                self._sync_story_state()
            return
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
    def gallery_options(self):
        return (('CS00', 'Awal perjalanan'),
                *((fragment.scene, fragment.title) for fragment in STORY_FRAGMENTS),
                ('CS07', 'Ujung jalan'), ('CS08', 'Adegan terakhir'))

    def _sync_story_state(self):
        self.audio.set_muted(self.muted or self.story.active == 'CS07')
        self.pending_action = self.pending_shift = False
        self.interaction_held = self.phase_held = False
        self.accumulator = 0.0
        if self.story.active:
            self.state = 'cutscene'
        elif self.story.replay:
            self.story.replay = False
            self.state = 'gallery'
        else:
            self.state = 'ending' if self.story.completed else 'playing'
        self._save()

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
        if self.state == 'cutscene':
            active = self.story.active
            if active != 'CS07' and not self.story.paused:
                self.audio.update(dt, 0, 1.0, ending=active == 'CS08')
            self.story.tick(dt)
            if self.story.active != active:
                self._sync_story_state()
            return
        self.visual_time+=dt
        self.notice_timer=max(0,self.notice_timer-dt)
        self.audio.update(dt,self.lantern.band,self.lantern.illumination,
                          boss=self.boss is not None and self.boss.phase>=1,
                          phase=self.world.phase,ending=self.state=='ending')
        if self.state=='ending':
            if self.cinematics_enabled:
                return
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
        if self.cinematics_enabled and not self.world.dead:
            for fragment in STORY_FRAGMENTS:
                if fragment.key not in self.story.collected and math.dist((px, py), fragment.position) < 52:
                    self.story.collect(fragment.key)
                    self.journal[f'fragment:{fragment.key}'] = fragment.title
                    self.audio.play('memory', .4)
                    if self.story.active:
                        self.state = 'cutscene'
                        self.pending_action = self.pending_shift = False
                        self.accumulator = 0.0
                    self._save()
                    return
        for f in FRAGMENTS:
            if self.cinematics_enabled:
                break
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
                label='DALAM HATI: ' if self.cinematics_enabled else 'NUR · DALAM HATI: '
                self._say(label+INWARD[self.lantern.band],5)
        if self.boss is not None and self.room==config.BOSS_ARENA_ROOM and not self.world.dead:
            self._handle_boss_event(self.boss.update(dt,(px,py),control.action,self.lantern.illumination,self.lantern.protects))
        elif self.cinematics_enabled and self.room == len(REGIONS)-1 and not self.world.dead:
            if px >= WORLD_WIDTH-180:
                if self.story.request_finale():
                    self._sync_story_state()
                    return
                if self.notice_timer <= 0:
                    self._say('Masih ada benda yang tertinggal. J · peta jalan / K · fragmen.', 6)
        if self.world.dead:
            self.death_timer+=dt
            if self.death_timer>1.05:
                self.lantern.die()
                self.restart_room()
            return
        target=max(0,min(WORLD_WIDTH-config.SIZE[0],px-config.SIZE[0]*.42))
        self.camera+=(target-self.camera)*min(1,dt*4)


