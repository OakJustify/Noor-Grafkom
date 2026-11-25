"""Original continuous light-reactive soundscape; non-verbal, no fake voice acting."""

import numpy as np
import pygame
from scipy.signal import butter, sosfilt

from .audio import RATE, Audio


def render_drift(kind, seconds=12):
    t=np.arange(round(seconds*RATE))/RATE
    rng=np.random.default_rng(400+kind)
    wind=sosfilt(butter(3,650,fs=RATE,output='sos'),rng.normal(size=len(t)))
    if kind==0:
        sound=(np.sin(2*np.pi*196*t)*.06+np.sin(2*np.pi*294*t)*.025+wind*.035)
    elif kind==1:
        sound=(np.sin(2*np.pi*73*t)*.08+np.sin(2*np.pi*77*t)*.05+wind*.075)
    else:
        # Formant-like breath and beating dissonance, not intelligible speech.
        envelope=.2+.8*np.sin(np.pi*t/3)**4
        sound=(np.sin(2*np.pi*49*t)*.09+np.sin(2*np.pi*51*t)*.06+
               wind*.15*envelope+np.sin(2*np.pi*387*t)*.025*envelope)
    fade=np.minimum(1,np.minimum(t,seconds-t)/.35)
    sound*=fade
    stereo=np.column_stack((sound,sound*(.93+.07*np.sin(t*np.pi/3))))
    return (np.clip(stereo,-.8,.8)*32767).astype(np.int16)


class Soundscape(Audio):
    def __init__(self,enabled=True):
        super().__init__(enabled)
        self.drift_targets=(0.,0.,0.)
        self.drift_channels=[]
        self.drift_sounds=[]
        self.hallucination_intensity=0.0
        if self.available:
            pygame.mixer.set_num_channels(max(18,pygame.mixer.get_num_channels()))
            pygame.mixer.set_reserved(10)
            for kind in range(3):
                self.drift_sounds.append(pygame.sndarray.make_sound(render_drift(kind)))
                channel=pygame.mixer.Channel(7+kind)
                channel.set_volume(0)
                self.drift_channels.append(channel)

    def update(self,dt,stage,illumination,boss=False,phase=0,ending=False):
        self.music_scene='return' if ending else 'gaung' if phase or boss else 'home'
        stress=1-illumination
        weird=max(0.0,min(1.0,self.hallucination_intensity))
        self.drift_targets=((.2*illumination*(1-.35*weird),.24*stress*(1+.65*weird),
                             .25*max(0,(.45-illumination)/.45)*(1+.8*weird)+.08*weird)
                            if not ending else (0.,0.,0.))
        if not self.enabled or not self.available:
            return
        for key in self.cooldowns:
            self.cooldowns[key]=max(0,self.cooldowns[key]-dt)
        # Replace inherited constant horror beds: warmth genuinely starts quiet.
        for name,channel in self.channels.items():
            if name!='boss_pulse':
                channel.set_volume(0)
        for scene,sound in self.music.items():
            channel=self.music_channels[scene]
            if not channel.get_busy():
                channel.play(sound,loops=-1)
            target=(.16+.13*illumination) if scene==self.music_scene else 0
            value=channel.get_volume()+(target-channel.get_volume())*min(1,dt*1.2)
            channel.set_volume(target if abs(target-value)<.015 else value)
        pulse=self.channels['boss_pulse']
        if boss and not ending:
            if not pulse.get_busy():
                pulse.play(self.sounds['boss_pulse'],loops=-1)
            pulse.set_volume(.18)
        else:
            pulse.stop()
        for sound,channel,target in zip(self.drift_sounds,self.drift_channels,self.drift_targets):
            if not channel.get_busy():
                channel.play(sound,loops=-1)
            current=channel.get_volume()
            value=current+(target-current)*min(1,dt*1.5)
            channel.set_volume(target if abs(target-value)<.015 else value)

    def set_muted(self,muted):
        super().set_muted(muted)
        for channel in self.drift_channels:
            channel.set_volume(0)

    def close(self):
        super().close()
        for channel in self.drift_channels:
            channel.stop()
