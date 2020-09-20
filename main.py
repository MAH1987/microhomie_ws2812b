import neopixel
import settings
import colorsys
import uasyncio as asyncio
import time

from machine import Pin


from homie.node import HomieNode
from homie.device import HomieDevice
from homie.property import HomieNodeProperty
from homie.constants import TRUE, FALSE, BOOLEAN, COLOR, RGB, ENUM, INTEGER

BLACK = (0, 0, 0)

DEFAULT = "159,140,170"

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

def fill_solid_rainbow(self):
    leds = settings.LEDS
    deltahue = 1 / leds
    b = int(4 + 3.1 * (self._brightness + 1) ** 2)
    r = range(leds)
    for l in r:
        rgb = list(colorsys.hsv_to_rgb(deltahue * l, 1, 1))
        color = (
            int(b * rgb[0] / 255),
            int(b * rgb[1] / 255),
            int(b * rgb[2] / 255)
        )
        set_led(self.np, l, color)

async def fill_fluid_rainbow(self):
    try:
        leds = settings.LEDS
        deltahue = 1 / leds
        b = int(4 + 3.1 * (self._brightness + 1) ** 2)
        r = range(leds)
        for l in r:
            rgb = list(colorsys.hsv_to_rgb(deltahue * l, 1, 1))
            color = (
                int(b * rgb[0] / 255),
                int(b * rgb[1] / 255),
                int(b * rgb[2] / 255)
            )
            set_led(self.np, l, color)

        while True:
            for l in r:
                if l < (leds - 1):
                    rgb = self.np[l+1]
                else:
                    rgb = self.np[0]

                color = (
                    int(rgb[0]),
                    int(rgb[1]),
                    int(rgb[2])
                )
                set_led(self.np, l, color)
                if self.rainbow_property.data != 'Fluid Rainbow':
                    break

            if self.rainbow_property.data != 'Fluid Rainbow':
                break
    finally:
        pass

class AmbientLight(HomieNode):
    def __init__(self, pin=settings.DATA_PIN, leds=settings.LEDS):
        super().__init__(
            id="light", name="Desklamp", type="WS2812B"
        )
        self._brightness = 4

        self.np = neopixel.NeoPixel(Pin(pin), leds)

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
            format="Aus,Solid Rainbow,Fluid Rainbow,Demo",
            default='Aus'
        )
        self.add_property(self.rainbow_property, self.on_rainbow_msg)
        
    @property
    def brightness(self):
        return self._brightness

    @brightness.setter
    def brightness(self, val):
        v = min(max(val, 0), 8)
        self._brightness = int(4 + 3.1 * (v + 1) ** 2)

        if self.power_property.data == TRUE:
            rgb = convert_str_to_rgb(self.color_property.data)
            self.on(rgb=rgb)

    def on(self, rgb):
        b = self._brightness
        color = (
            int(b * rgb[0] / 255),
            int(b * rgb[1] / 255),
            int(b * rgb[2] / 255)
        )
        all_on(self.np, color=color)

    def on_power_msg(self, topic, payload, retained):
        if payload == TRUE:
            rgb = convert_str_to_rgb(self.color_property.data)
            self.on(rgb=rgb)
        elif payload == FALSE:
            all_off(self.np)
        else:
            return

        self.power_property.data = payload

    def on_color_msg(self, topic, payload, retained):
        rgb = convert_str_to_rgb(payload)
        if rgb is not None:
            self.color_property.data = payload
            if self.power_property.data == TRUE:
                self.on(rgb=rgb)

    def on_brightness_msg(self, topic, payload, retained):
        try:
            b = min(max(int(payload), 1), 8)
            self.brightness = b
            self.brightness_property.data = payload
        except ValueError:
            pass

    def on_rainbow_msg(self, topic, payload, retained):
        try:            
            rainbow_type = payload
            if rainbow_type == 'Solid Rainbow':            
                self.rainbow_property.data = rainbow_type
                fill_solid_rainbow(self)
                return
            elif rainbow_type == 'Fluid Rainbow':
                self.rainbow_property.data = rainbow_type
                self._task = asyncio.create_task(fill_fluid_rainbow(self))
                return
            elif rainbow_type == 'Demo':
                print('Demo')
                n = self.np.n

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
                self.rainbow_property.data = rainbow_type
                rgb = convert_str_to_rgb(self.color_property.data)
                self.on(rgb=rgb)                
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
