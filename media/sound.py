# -*- coding: utf-8 -*-
import os
import time
import pygame
import threading
from typing import *
from ..core.timer import SwTimer
__all__ = ['SoundPlay']


class SoundPlay(object):
    def __init__(self, lib: str, music_volume: float = 0.5, effect_volume: float = 0.3):
        self.__lib = lib
        self.__effect = None
        self.__paused = False
        self.__music_volume = music_volume
        self.__effect_volume = effect_volume
        self.__stop_music_callback = None
        self.__timer = SwTimer(base=1.0, callback=self.__callback)

        pygame.mixer.init()
        pygame.mixer.music.set_volume(music_volume)

    def __del__(self):
        pygame.mixer.quit()

    def __callback(self, timer: SwTimer):
        if not self.is_playing:
            timer.pause()
            if callable(self.__stop_music_callback):
                self.__stop_music_callback(timer.time_elapsed())

    @property
    def is_paused(self) -> bool:
        return self.__paused

    @property
    def is_playing(self) -> bool:
        return pygame.mixer.music.get_busy() and not self.is_paused

    @property
    def music_volume(self) -> float:
        return self.__music_volume if not self.is_playing else pygame.mixer.music.get_volume()

    @property
    def effect_volume(self) -> float:
        return self.__effect.get_volume() if isinstance(self.__effect, pygame.mixer.Sound) else self.__effect_volume

    @music_volume.setter
    def music_volume(self, volume: float):
        pygame.mixer.music.set_volume(volume)
        self.__music_volume = pygame.mixer.music.get_volume()

    @effect_volume.setter
    def effect_volume(self, volume: float):
        if isinstance(self.__effect, pygame.mixer.Sound):
            self.__effect.set_volume(volume)
            self.__effect_volume = self.__effect.get_volume()
        else:
            self.__effect_volume = volume

    def stop(self):
        if self.is_playing:
            pygame.mixer.music.stop()

    def pause(self):
        if not pygame.mixer.get_busy():
            return

        if self.__paused:
            pygame.mixer.pause()
            self.__paused = True
        else:
            pygame.mixer.unpause()
            self.__paused = False

    def increase_music_volume(self, step: float = 0.1) -> float:
        if not self.is_playing:
            return self.music_volume

        volume = pygame.mixer.music.get_volume() + step
        pygame.mixer.music.set_volume(1.0 if volume > 1.0 else volume)
        return self.music_volume

    def decrease_music_volume(self, step: int = 0.1):
        if not self.is_playing:
            return self.music_volume

        volume = pygame.mixer.music.get_volume() - step
        pygame.mixer.music.set_volume(0.0 if volume < 0.0 else volume)
        return self.music_volume

    @staticmethod
    def volume_auto_control(volume_control: Callable[[float], float],
                            volume_cmp: Callable[[float], bool],
                            step: float = 0.1, interval: int = 5):
        while True:
            time.sleep(interval)
            volume = volume_control(step)
            print("Current volume: {}".format(volume))
            if volume_cmp(volume):
                break

        print("Volume auto control stopped")

    def play_se(self, name: str, loops: int = 0, max_time_ms: int = 0, volume: Optional[float] = None) -> bool:
        if name not in os.listdir(self.__lib):
            print("Sound effect {!r} not exist".format(name))
            return False

        try:
            self.__effect = pygame.mixer.Sound(os.path.join(self.__lib, name))
            if isinstance(volume, float) and 0.1 <= volume <= 1.0 and self.__effect.get_volume() != volume:
                self.__effect.set_volume(volume)

            self.__effect.play(loops, maxtime=max_time_ms)
            return True
        except pygame.error as e:
            print("Play music error: {}".format(e))
            return False

    def play_music(self, name: str,
                   start: int = 0, times: int = -1, volume: Optional[float] = None,
                   stop_callback: Optional[Callable[[str, int, float], None]] = None) -> bool:
        if name not in os.listdir(self.__lib):
            print("Background music {!r} not exist".format(name))
            return False

        try:
            pygame.mixer.music.load(os.path.join(self.__lib, name))
            if isinstance(volume, float) and 0.1 <= volume <= 1.0 and pygame.mixer.music.get_volume() != volume:
                pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(times, start)

            if times != -1 and callable(stop_callback):
                self.__stop_music_callback = lambda play_time: stop_callback(name, start, play_time)
                self.__timer.reset()
                self.__timer.resume()
            else:
                self.__timer.pause()

            return True
        except pygame.error as e:
            print("Play music error: {}".format(e))
            return False

    def auto_increase_volume(self, step: float = 0.1, maximum: float = 1.0, interval: int = 5):
        args = (self.increase_music_volume, lambda x: x >= maximum, step, interval)
        th = threading.Thread(target=self.volume_auto_control, args=args, name="Auto increase volume")
        th.setDaemon(True)
        th.start()

    def auto_decrease_volume(self, step: float = 0.1, minimum: float = 0.0, interval: int = 5):
        args = (self.decrease_music_volume, lambda x: x <= minimum, step, interval)
        th = threading.Thread(target=self.volume_auto_control, args=args, name="Auto decrease volume")
        th.setDaemon(True)
        th.start()
