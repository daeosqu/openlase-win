# OpenLase for Windows

This was forked from [marcan/openlase](https://github.com/marcan/openlase)

See [README-QuickStart.md](./README-QuickStart.md) for instructions.

![screenshot](https://github.com/daeosqu/openlase-win/blob/master/screenshot.png)

## Enviroment variables

- `OL_JACK_VERBOSE`: 0-2 (default 1) - jack verbose level
- `PYPLAYVID_AUDIO_CHECKS`: BOOL (default 0) - enable audio runtime diagnostics
- `PYPLAYVID_AUDIO_UNDERFLOW_INTERVAL`: FLOAT (default 1.0) - minimum seconds between underflow log messages

TODO remove PYPLAYVID_AUDIO_CHECKS and debug code from audio.py


## Python demos

Two lightweight sample programs showcase the pure Python backends bundled with
this repository:

- ``python -m pylasepure.demo.cli`` animates a colourful Lissajous curve using
  the Qt renderer.  Use ``--help`` to customise the duration, point count, and
  colour palette.
- ``python -m purelase.demo.cli`` initialises the JACK-compatible stub backend
  and prints statistics from the simulated audio callback without requiring an
  actual JACK server.



