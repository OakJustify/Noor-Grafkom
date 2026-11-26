"""Rendering of the v4 world, HUD, journal, menu, pause and ending screens."""

from __future__ import annotations

import math

import pygame

from .. import config
from ..continuum import REGIONS, WORLD_WIDTH
from ..cinematics.fragments import STORY_FRAGMENTS


class PresentationMixin:
    def draw(self):
        screen=self.canvas
        if self.cinematics_enabled and self.state == 'cutscene' and self.story.active:
            return self.cinema.draw(screen, self.story.scene, self.story.cue, self.story.cue_elapsed,
                                    self.story.scene_elapsed, self.story.paused)
        if self.cinematics_enabled and self.state == 'ending':
            return self.cinema.draw_ending(screen, self.ending_page, self.visual_time)
        if self.state == 'gallery':
            return self._draw_gallery()
        px,py=self._player_xy()
        self.art.draw_background(screen,self.camera,self.room,self.visual_time,player_x=px)
        if self.world.quest:
            self.world.quest.draw_space(screen,self.camera,(px,py))
        self.art.draw_world_terrain(screen,self.world,self.camera,self.lantern.illumination)
        for trap in self.world.hazards.machines:
            if abs(trap.x-px)<245 and self.lantern.charge>0:
                from ..hazards import KINDS
                hint=("Tombol merah menjatuhkan besi", "Duri mematikan", "Tunggu semburan berhenti",
                      "Kawat merah menjatuhkan balok", "Tunggu ayunan lewat")[trap.kind]
                self._text(KINDS[trap.kind]+" · "+hint,480,187,16,(245,185,142),center=True)
        for r in REGIONS:
            x=r.refuge[0]-self.camera
            if -100<x<config.SIZE[0]+100:
                self.art.draw_refuge(screen,x,r.index in self.refuges.visited)
                if math.dist((px,py),r.refuge)<75:
                    self._text("E · STASIUN SUMBU",max(115,x),355,14,config.WAX,center=True)
            if r.index<len(REGIONS)-1 and r.index not in self.refuges.threads:
                tx=r.start+r.source.level.width+365-self.camera
                if -30<tx<config.SIZE[0]+30:
                    pygame.draw.lines(screen,(239,168,145),False,[(tx-9,296),(tx+8,301),(tx-7,310),(tx+9,319)],4)
                    if abs(px-self.camera-tx)<45 and abs(py-328)<42:
                        self._text("E · PITA",tx,269,14,config.WAX,center=True)
        self.threats.draw(screen,self.camera,self.lantern)
        if self.cinematics_enabled:
            for fragment in STORY_FRAGMENTS:
                if fragment.key in self.story.collected:
                    continue
                fx, fy = fragment.position
                sx = fx-self.camera
                if -60 < sx < config.SIZE[0]+60:
                    self.cinema.draw_fragment(screen, fragment.key, sx, fy-28, self.visual_time)
                    if math.dist((px, py), (fx, fy)) < 140:
                        self._text('Sentuh · '+fragment.title, max(110, min(850, sx)), fy-96, 16, config.WAX, center=True)
        self.phantoms.draw(screen,self.camera)
        if self.boss and self.room==config.BOSS_ARENA_ROOM:
            self.boss.draw(screen,self.camera,self.lantern.illumination)
        if self.world.quest:
            self.world.quest.draw(screen,self.camera,self.fonts[14],self.visual_time,(px,py),self.world.phantom_shapes)
        self.art.draw_player(screen,(px,py),self.camera,self.lantern.illumination,self.world.facing,
                             self.visual_time,self.world.player.velocity,self.world.grounded,self.player_animation,
                             carried=self.lantern.carried)
        if self.planted:
            x,y=self.planted[0]-self.camera,self.planted[1]
            pygame.draw.rect(screen,(233,184,104),(x-6,y+8,13,18),border_radius=3)
        self.art.draw_foreground(screen,self.camera,self.room,(px-self.camera,py),self.visual_time)
        origin=self.light_origin
        self.art.grade(screen,(origin[0]-self.camera,origin[1]),self.lantern,self.visual_time)
        self.hallucination_visuals.apply(screen,self.sanity.current_sanity,self.sanity.max_sanity,self.visual_time)
        if self.cinematics_enabled:
            self._grade_story(screen)
        if self.state!='menu':
            self._draw_hud()
        if self.notice_timer and self.state=='playing':
            self._caption(self.notice,162 if self.developer_mode else 109,16,min(255,round(self.notice_timer*150)))
        if self.world.dead:
            self._caption(self.world.death_reason,250,21,255)
        if self.lantern.charge<=0 and self.state=='playing':
            self._caption("CAHAYA PADAM\nE · kembali ke stasiun sumbu terakhir",231,21,255)
        if self.boss and self.room==28 and self.state=='playing' and self.lantern.charge>0:
            if self.boss.phase==1:
                self._caption("NUR · DALAM HATI: "+self.boss.line,213,18,255)
                self._text(f"Dekati gaung · tahan E untuk meminta ditemani ({self.boss.name_presses}/3)",480,294,16,config.WAX,center=True)
            elif self.boss.phase==0:
                self._text(f"Dekati tiga benda yang masih berpendar · {sum(e['taken'] for e in self.boss.echoes)}/3",480,181,16,config.WAX,center=True)
        if self.state=='journal':
            self._draw_journal()
        elif self.state=='menu':
            self._draw_menu()
        elif self.state=='paused':
            self._draw_pause()
        elif self.state=='ending':
            self._draw_ending()
        if self.developer_mode and self.state in ('playing', 'paused'):
            pygame.draw.rect(screen, (23, 40, 53), (14, 88, 932, 48), border_radius=5)
            self._text('DEVELOPER · Save nonaktif · F7 void / F8 ending / F9 penutup', 28, 93, 14, config.WAX)
            self._text('F1 pita   F2 cangkir   F3 kunci   F4 foto   F5 resep   F6 kain', 28, 114, 14, config.BONE)
        return screen

    def _draw_gallery(self):
        self.canvas.fill((28, 44, 59))
        self._text('FRAGMEN', 50, 28, 32, config.WAX)
        self._text(f'{len(self.story.collected)}/6 benda ditemukan · adegan terbuka bisa diputar ulang', 50, 77, 16, config.BONE)
        for index, (key, title) in enumerate(self.gallery_options):
            y = 120+index*36
            unlocked = key in self.story.seen
            if index == self.gallery_page:
                pygame.draw.rect(self.canvas, (53, 74, 87), (42, y-4, 596, 33), border_radius=5)
                pygame.draw.line(self.canvas, config.WAX, (43, y-4), (43, y+29), 3)
            self._text(f'{index+1:02d}', 58, y, 16, config.WAX if unlocked else (139, 157, 162))
            self._text(title, 101, y, 18, config.BONE if unlocked else (139, 157, 162))
            self._text('TERBUKA' if unlocked else 'BELUM TERBUKA', 470, y+2, 14, config.WAX if unlocked else (139, 157, 162))
        selected = next((f for f in STORY_FRAGMENTS if f.scene == self.gallery_options[self.gallery_page][0]), None)
        pygame.draw.circle(self.canvas, (41, 60, 74), (785, 248), 93)
        if selected and selected.key in self.story.collected:
            self.cinema.draw_fragment(self.canvas, selected.key, 785, 248)
            self._text(selected.title, 785, 365, 21, config.WAX, center=True)
        else:
            self._text('?', 785, 230, 32, config.BONE, center=True)
        self._text('↑/↓ pilih · ENTER putar · K/ESC kembali', 480, 495, 16, config.WAX, center=True)
        return self.canvas

    def _grade_story(self, screen):
        fade = self.story.fade
        if fade <= 0:
            return
        grey = pygame.transform.grayscale(screen)
        grey.set_alpha(round(min(1.0, fade * 1.2) * 255))
        screen.blit(grey, (0, 0))
        gain = round(255 * (1 - fade * .78))
        screen.fill((gain, gain, gain), special_flags=pygame.BLEND_RGB_MULT)

    def _draw_hud(self):
        panel=pygame.Surface((932,72),pygame.SRCALPHA)
        panel.fill((30,49,65,220))
        self.canvas.blit(panel,(14,12))
        self._text(f"JALAN PULANG · {REGIONS[self.room].source.name}",28,22,18,(248,220,178))
        if self.cinematics_enabled:
            self._text(f'{len(self.story.collected)}/6 · K FRAGMEN · J PETA', 740, 25, 14, config.BONE)
        else:
            self._text(f"{self.world.player.position.x/1000:.1f} / {WORLD_WIDTH/1000:.1f}  ·  J PETA",740,25,14,config.BONE)
        if self.world.quest:
            q=self.world.quest
            self._text(f"{q.stage}/6 · {q.instruction}",28,51,14,(193,222,211))
        else:
            self._text("E sumbu · Q gaung · H ilusi · Shift lari · F cahaya · G lentera",28,51,14,(193,222,211))
        base=pygame.Surface((960,50),pygame.SRCALPHA)
        base.fill((23,40,53,225))
        self.canvas.blit(base,(0,490))
        self._text("CAHAYA",23,500,12,config.WAX)
        pygame.draw.rect(self.canvas,(52,70,81),(85,507,126,7),border_radius=3)
        pygame.draw.rect(self.canvas,(241,192,123),(85,507,round(126*self.lantern.charge),7),border_radius=3)
        self._text("NAPAS",239,500,12,(179,220,203))
        pygame.draw.rect(self.canvas,(52,70,81),(295,507,100,7),border_radius=3)
        pygame.draw.rect(self.canvas,(147,205,186),(295,507,round(100*self.stamina.amount),7),border_radius=3)
        self._text("PULIH" if self.stamina.exhausted else "LARI" if self.world.sprinting else "JALAN",407,500,12,config.BONE)
        self._text(f"Q · {('NYATA','GAUNG')[self.world.phase]}  PITA {len(self.refuges.threads)-len(self.refuges.delivered)}",505,500,12,config.BONE)
        ratio=max(0.0,min(1.0,self.sanity.normalized))
        sanity_colour=(round(236-96*ratio),round(126+70*ratio),round(100+50*ratio))
        self._text("H · ILUSI" if self.sanity.hallucinating else "TENANG",610,500,12,sanity_colour)
        pygame.draw.rect(self.canvas,(52,70,81),(650,507,92,7),border_radius=3)
        pygame.draw.rect(self.canvas,sanity_colour,(650,507,round(92*ratio),7),border_radius=3)
        self._text("LENTERA DI TANGAN" if self.lantern.carried else "G · AMBIL LENTERA",758,500,12,config.WAX)

    def _draw_journal(self):
        self.canvas.fill((28,44,59))
        self._text("ATLAS JALAN PULANG",480,24,32,(246,218,174),center=True)
        for r in REGIONS:
            x=45+r.start/WORLD_WIDTH*870
            colour=(234,186,117) if r.index in self.world.quests and self.world.quests[r.index].complete else (97,143,148)
            pygame.draw.line(self.canvas,colour,(x,90),(45+r.end/WORLD_WIDTH*870,90),5)
        px=45+self.world.player.position.x/WORLD_WIDTH*870
        pygame.draw.circle(self.canvas,(255,235,188),(round(px),90),7)
        if self.cinematics_enabled:
            for fragment in STORY_FRAGMENTS:
                if fragment.key not in self.story.collected:
                    x=round(45+fragment.position[0]/WORLD_WIDTH*870)
                    pygame.draw.circle(self.canvas,config.WAX,(x,90),5,2)
            self._text('Lingkaran kosong: benda yang belum ditemukan · K untuk memutar fragmen', 480, 134, 14, config.WAX, center=True)
        if self.planted:
            pygame.draw.circle(self.canvas,(238,156,102),(round(45+self.planted[0]/WORLD_WIDTH*870),90),4)
        self._text("Rumah    Desa / laut    Arsip    Hutan    Perawatan    Pulang",480,110,14,config.BONE,center=True)
        entries=list(self.journal.items())
        pages=max(1,(len(entries)+1)//2)
        self.journal_page=min(self.journal_page,pages-1)
        for n,(key,text) in enumerate(entries[self.journal_page*2:self.journal_page*2+2]):
            self._text(key.upper(),60,167+n*145,16,config.WAX)
            self._caption(text,203+n*145,16,255)
        if not entries:
            self._caption("Rawat sumbu, ingat gaung dan simpan pita. Waspadai tombol merah dan mesin yang masih bergerak.",209,18,255)
        self._text(f"{self.journal_page+1}/{pages} · ←/→ halaman · J/ESC kembali",480,488,16,config.WAX,center=True)

    def _canvas_point(self, point):
        width, height = self.display.get_size()
        return (point[0]*self.canvas.get_width()/max(1, width),
                point[1]*self.canvas.get_height()/max(1, height))

    def _developer_button_rect(self):
        return pygame.Rect((self.canvas.get_width()-280)//2, 378, 280, 48)

    def _draw_menu(self):
        if self.cinematics_enabled:
            self._caption('NOOR\nYang masih di sini',145,32,255)
            self._caption('Telusuri jalan. Temukan benda yang tertinggal.\nENTER mulai · C lanjut · M suara',294,18,255)
            button = self._developer_button_rect()
            hover = button.collidepoint(self._canvas_point(pygame.mouse.get_pos()))
            pygame.draw.rect(self.canvas, (53, 74, 87) if hover else (30, 49, 65), button, border_radius=6)
            pygame.draw.rect(self.canvas, config.WAX, button, 2 if hover else 1, border_radius=6)
            self._text('D · MODE DEVELOPER', button.centerx, button.y+13, 18, config.WAX, center=True)
            self._text('Latihan fragmen & ending · tanpa save', button.centerx, button.bottom+10, 14, config.BONE, center=True)
            return
        self._caption("NUR\nTHE LONG WAY HOME",145,32,255)
        self._caption("Ingatan, cahaya, dan mesin yang tidak pernah berhenti.\nENTER mulai · C lanjut · M suara",294,18,255)

    def _draw_pause(self):
        self._caption("ISTIRAHAT\nESC kembali · R kembali ke stasiun terakhir\nCahaya dan napas berhenti berkurang saat istirahat.",203,21,255)

    def _draw_ending(self):
        # No NPC figures: the ending shows the player and its surviving flame.
        self.art.draw_background(self.canvas,self.camera,28,self.visual_time)
        pygame.draw.rect(self.canvas,(95,109,115),(0,446,960,94))
        self.art.draw_refuge(self.canvas,560,True)
        self.art.draw_player(self.canvas,(475,425),0,1,1,self.visual_time,
                             animation=self.player_animation)
        pages=(
            ("PULANG BUKAN SEBUAH NAMA","Mesin di belakang masih berbunyi.\nDi sini, kau bisa berhenti."),
            ("JEJAK YANG TERTINGGAL",f"{len(self.refuges.visited)} stasiun sumbu menjadi tanda pulang.\n{len(self.refuges.delivered)} pita ditinggalkan di sepanjang jalan."),
            ("CAHAYA YANG DIRAWAT","Ingatan tidak pulih karena satu perjalanan.\nTetapi bara kecil ini belum padam."),
            ("SATU LANGKAH LAGI","Besok mungkin jalan ini tampak asing lagi.\nHari ini, kau sampai."),
        )
        title,text=pages[min(self.cutscene_index,3)]
        self._caption(title,90,26,255)
        self._caption(text,170,21,255)
        self._text("ENTER mulai lagi · ESC keluar",480,499,16,(248,216,177),center=True)
