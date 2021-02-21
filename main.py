import neopixel
import settings
import colorsys
import uasyncio as asyncio
import time

from machine import Pin
from uasyncio import sleep_ms

from homie.node import HomieNode
from homie.device import HomieDevice
from homie.property import HomieNodeProperty
from homie.constants import TRUE, FALSE, BOOLEAN, COLOR, RGB, ENUM, INTEGER

BLACK = (0, 0, 0)

DEFAULT = "171,20,158"

def all_off(np):
    np.fill(BLACK)
    np.write()

def all_on(np, color=DEFAULT):
    np.fill(color)
    np.write()

def set_leds(np, start, end, color=BLACK, autowrite=True):
    r = range(start, end)
    for i in r:
        np[i] = color
    if autowrite:
        np.write()

def set_led(np, led, color=BLACK, autowrite=True):
    np[led] = color
    if autowrite:
        np.write()

def convert_str_to_rgb(rgb_str):
    try:
        r, g, b = rgb_str.split(",")
        return (int(r.strip()), int(g.strip()), int(b.strip()))
    except (ValueError, TypeError):
        return None

def fill_solid_rainbow(cls):
    try:
        for l in cls._range:
            rgb = list(colorsys.hsv_to_rgb(cls._deltahue * l, 1, 1))
            color = (
                int( cls._brightness * (rgb[0] * 255) / 255 ),
                int( cls._brightness * (rgb[1] * 255) / 255 ),
                int( cls._brightness * (rgb[2] * 255) / 255 )
            )
            cls.np[l] = color
        cls.np.write()
    finally:
        pass

async def fill_fluid_rainbow(cls):
    try:
        while True:
            for l in cls._range:
                if l < (cls._leds - 1):
                    rgb = cls.np[l + 1]
                else:
                    rgb = cls.np[0]
                cls.np[l] = rgb
                if cls.rainbow_property.data != 'Fluid Rainbow':
                    break
            cls.np.write()
            await asyncio.sleep_ms(0)
            if cls.rainbow_property.data != 'Fluid Rainbow':
                break
    finally:
        pass

async def fill_effect(cls, effect):
    try:
        heaps = [
            (0, 0, 0),
            (46, 18, 0),
            (96, 113, 0),
            (108, 142, 3),
            (119, 175, 17),
            (146, 213, 44),
            (174, 255, 82),
            (188, 255, 115)
        ]
        hr = range(len(heaps))

        for l in cls._range:
            color = (
                int( 0 ),
                int( 0 ),
                int( 0 )
            )
            set_led(cls.np, l, color)
        l = 0
        while True:
            for c in hr:
                set_led(cls.np, l, heaps[c-1])
                l += 1
                if l >= cls._led:
                    l = 0
                if cls.rainbow_property.data != 'Lava':
                    break
            await asyncio.sleep_ms(15)
            if cls.rainbow_property.data != 'Lava':
                break
    finally:
        pass


class AmbientLight(HomieNode):
    def __init__(self, pin=settings.DATA_PIN, leds=settings.LEDS):
        super().__init__(
            id="light", name="Desklamp", type="WS2812B"
        )
        ##############################
        # define basic vars
        ##############################
        self._brightness = 4
        self._leds = settings.LEDS
        self._deltahue = 1 / self._leds
        self._range = range(self._leds)
        ##############################
        # define neopixels
        ##############################
        self.np = neopixel.NeoPixel(Pin(pin), self._leds)
        ##############################
        # define probertiys
        ##############################
        self.power_property = HomieNodeProperty(
            id="power",
            name="Light power",
            settable=True,
            datatype=BOOLEAN,
            default=FALSE,
        )
        self.add_property(self.power_property, self.on_power_msg)

        self.color_property = HomieNodeProperty(
            id="color",
            name="RGB Color",
            settable=True,
            datatype=COLOR,
            default=DEFAULT,
            format=RGB,
        )
        self.add_property(self.color_property, self.on_color_msg)

        self.brightness_property = HomieNodeProperty(
            id="brightness",
            name="LED brightness",
            settable=True,
            datatype=ENUM,
            format="1,2,3,4,5,6,7,8",
            default=4,
        )
        self.add_property(self.brightness_property, self.on_brightness_msg)

        self.rainbow_property = HomieNodeProperty(
            id="rainbow",
            name="Rainbow",
            settable=True,
            datatype=ENUM,
            restore=False,
            format="Aus,Solid Rainbow,Fluid Rainbow,Demo,Lava",
            default='Aus'
        )
        self.add_property(self.rainbow_property, self.on_rainbow_msg)
        
    @property
    def brightness(cls):
        return cls._brightness

    @brightness.setter
    def brightness(cls, val):
        v = min(max(val, 0), 8)
        cls._brightness = int(4 + 3.1 * (v + 1) ** 2)

        if cls.rainbow_property.data == 'Solid Rainbow':
            fill_solid_rainbow(cls)
        elif cls.power_property.data == TRUE:
            rgb = convert_str_to_rgb(cls.color_property.data)
            cls.on(rgb=rgb)

    def on(self, rgb):
        b = self._brightness
        color = (
            int(self._brightness * rgb[0] / 255),
            int(self._brightness * rgb[1] / 255),
            int(self._brightness * rgb[2] / 255)
        )
        all_on(self.np, color=color)

    def on_power_msg(cls, topic, payload, retained):
        cls.power_property.data = payload
        if payload == TRUE:
            rgb = convert_str_to_rgb(self.color_property.data)
            cls.on(rgb=rgb)
        elif payload == FALSE:
            all_off(cls.np)
        else:
            return

    def on_color_msg(cls, topic, payload, retained):
        rgb = convert_str_to_rgb(payload)
        if rgb is not None:
            cls.rainbow_property.data = 'Aus'
            if cls.power_property.data == TRUE:
                cls.on(rgb=rgb)

    def on_rainbow_msg(cls, topic, payload, retained):
        try:
            rainbow_type = payload
            if rainbow_type == 'Solid Rainbow':
                fill_solid_rainbow(cls)
                return

            elif rainbow_type == 'Fluid Rainbow':
                fill_solid_rainbow(cls)
                cls._task = asyncio.create_task(fill_fluid_rainbow(cls))

                return

            elif cls.rainbow_property.value == 'Lava':
                cls._task = asyncio.create_task(fill_effect(cls, 'Lava'))
                return

            elif cls.rainbow_property.value == 'Demo':
                print('Demo')
                n = cls.np.n
                # fade in/out
                for i in range(0, 4 * 256, 8):
                    for j in range(n):
                        if (i // 256) % 2 == 0:
                            val = i & 0xff
                        else:
                            val = 255 - (i & 0xff)
                        self.np[j] = (val, 0, 0)
                    self.np.write()

                # clear
                for i in range(n):
                    self.np[i] = (0, 0, 0)
                self.np.write()
                return

            else:
                rgb = convert_str_to_rgb(cls.color_property.data)
                cls.on(rgb=rgb)
                return

        except ValueError:
            pass

def main():
    homie = HomieDevice(settings)

    homie.add_node(
        AmbientLight()
    )

    homie.run_forever()

main()
