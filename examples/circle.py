#!python3
#         OpenLase - a realtime laser graphics toolkit
#
# Copyright (C) 2024 Daisuke Arai <daisuke.qu@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 or version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import math
import colorsys

if os.name == 'nt':
    os.add_dll_directory(r"C:\Windows")  # for find jack.dll

import pylase as ol


ol.init(3, 200000)

rate = 48000
min_rate = 15

params = ol.RenderParams()

params.rate = rate
params.render_flags = ol.RENDER_GRAYSCALE
params.on_speed = 2 / 60.0
params.off_speed = 1 / 30.0
params.min_length = 14
params.start_wait = 8
params.end_wait = 3
params.flatness = 0.00001
params.max_framelen = rate / min_rate
params.snap = 1/120.0
params.start_dwell = 0
params.end_dwell = 0
params.corner_dwell = 0
params.curve_dwell = 0
params.curve_angle = math.cos(30 * (math.pi / 180.0))

ol.setRenderParams(params)

ol.loadIdentity()
ol.scale((1, 1))

while True:
    ol.begin(ol.POINTS)
    for i in range(0, 100):
        x = math.cos(2 * math.pi * (i / 100))
        y = math.sin(2 * math.pi * (i / 100))
        r, g, b = colorsys.hsv_to_rgb(i / 100, 1, 1)
        r = int(r * 255)
        g = int(g * 255)
        b = int(b * 255)
        color = (r << 16) | (g << 8) | b
        ol.vertex((x, y), color)
    ol.end();
    ol.renderFrame(60)

