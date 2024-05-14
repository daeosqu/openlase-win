import sys

import cv2
from PIL import Image

import pylase as ol

cv2.namedWindow("preview")
if len(sys.argv) < 1:
    print("usage: mini_trace.py <CAMERA_NUMBER>", file=sys.stderr)
    exit(1)
vc = cv2.VideoCapture(int(sys.argv[1]))

width = int(vc.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(vc.get(cv2.CAP_PROP_FRAME_HEIGHT))

if vc.isOpened(): # try to get the first frame
    rval, frame = vc.read()
else:
    rval = False

#if ol.init(3, 40000) < 0: 40000 だと落ちた
if ol.init(3, 80000) < 0:
    exit(1)

params = ol.RenderParams()
params.render_flags = ol.RENDER_GRAYSCALE
params.on_speed = 2/60.0
params.off_speed = 1/30.0
params.end_wait = 0
params.start_wait = 20
params.flatness = 0.00001
params.max_framelen = 48000 / 25
params.min_length = 10
params.snap = 0.04

params.start_dwell = 0
params.end_dwell = 0
params.corner_dwell = 0
params.curve_dwell = 0

ol.setRenderParams(params)
ol.loadIdentity()
ol.scale((2, -2))
ol.translate((-0.5, -0.5))
mw = float(max(width, height))
print(width, height, mw)
ol.scale((1/mw, 1/mw))
ol.translate(((mw-width)/2, (mw-height)/2))

tracer = None

while rval:

    cv2.imshow("preview", frame)
    rval, frame = vc.read()

    cv2_im = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    im = Image.fromarray(cv2_im)

    im.save("a.png")

    im = im.convert('I')

    if tracer is None:
        width, height = im.size
        tracer = ol.Tracer(width, height)
        tracer.mode = ol.TRACE_CANNY
        tracer.threshold = 30
        tracer.threshold2 = 10
        tracer.sigma = 1.2

    s = im.tobytes('raw', 'I')
    if len(s) == (width * height * 4):
         s = s[::4] #XXX workaround PIL bug

    objects = tracer.trace(s)

    DECIMATE = 1
    nobjects = 0
    npoints = 0
    for o in objects:
        nobjects += 1
        if len(o) > DECIMATE:
            ol.begin(ol.POINTS)
            for point in o[::DECIMATE]:
                npoints += 1
                ol.vertex(point, ol.C_WHITE)
            ol.end()

    print("objects:{}, points:{}".format(nobjects, npoints))
    ol.renderFrame(60)

    key = cv2.waitKey(1)
    if key == 27: # exit on ESC
        break

cv2.destroyWindow("preview")
