# QuickStart

Quick start manual for OpenLase-win

# Requirements

Install OpenLase-win and download and install required software.

- [JACK 1.9.22 win64](https://github.com/jackaudio/jack2-releases/releases/download/v1.9.22/jack2-win64-v1.9.22.exe) JACK Audio Connection Kit for Windows 64bit
- AutoHotkey
- Python3.11 (C:\opt\python311)
- FFmpeg (`scoop install ffmpeg`)
- [laserdock_jack](https://github.com/daeosqu/laserdock_jack.git) if you have LaserCube

# Setup QjackCtl

1. Run `qjackctl` (`C:/Program Files/JACK2/qjackctl/qjackctl.exe`)
1. Push `Patchbay...` button.
  1. Push `Load...` button.
    1. Load 
    1. Push `Activate` button.
1. Push `Setup...` button.
  1. Set `Driver` to `portaudio` in Settings tab.
  1. Set parameters.
    - Sample Rate: 48000
    - Frames/Period: 1024
  1. Check `Start JACK audio server on application startup` in Misc tab.
  1. `Option` tab.
    1. Check `Activate Patchbay persistence` in Misc tab.
    1. And select file `share/openlase/openlase-laserjack.xml` in openlase directory.
1. Restart qjackctl

Important: Samplerate and bitrate must be same as windows audio device.

# Run openlase terminal

Start openlase-x.x.x in start menu or execute `source /usr/local/openlase/bin/openlase.sh` for bash.

# Setup (first time)

Install required python packages.

```powershel
python -m pip install click jaconv yt_dlp ffmpeg-python tinydb pillow opencv-contrib-python
```

# Start OpenLase environment

```powershel
olstart
```

# Run simple exaple

```
simple
```

# Play bad Apple

```
oldownload "https://www.nicovideo.jp/watch/sm8628149"
playvid (Get-Item $env:OL_DATA_DIR\media\*Bad_Apple*Shadow*.mp4)
```

# Bad Apple (Color)

```
oldownload "uOyaCOViAPA"
qplayvid (Get-Item $env:OL_DATA_DIR\media\*Bad_Apple*Color*.mp4)
```

# oldownload

Download youtube video into OL_DATA_DIR (~/.cache/openlase/media).

```
PS> oldownload "https://www.youtube.com/watch?v=a6-MraffDlE"
C:\Users\daisuke\.cache\openlase\media\003.a6-MraffDlE.MMD_ねこみみスイッチ_with_HachiBee.mp4
```

Or, simply specify id.

```
PS> oldownload "a6-MraffDlE"
```

List files downloaded by oldownload.

```
PS> oldownload -l
C:\Users\daisuke\.cache\openlase\media\001.uOyaCOViAPA.MMD_Bad_Apple___Now_in_3D_with_more_Color～.mp4
C:\Users\daisuke\.cache\openlase\media\002.sm8628149.［Touhou］_Bad_Apple___PV_［Shadow］.mp4
C:\Users\daisuke\.cache\openlase\media\003.a6-MraffDlE.MMD_ねこみみスイッチ_with_HachiBee.mp4

```

Download and print filename.

```
PS> oldownload "https://www.youtube.com/watch?v=a6-MraffDlE"
C:\Users\daisuke\.cache\openlase\media\003.a6-MraffDlE.MMD_ねこみみスイッチ_with_HachiBee.mp4
```

Print filename by id.

```
PS> oldownload --id 3
C:\Users\daisuke\.cache\openlase\media\003.a6-MraffDlE.MMD_ねこみみスイッチ_with_HachiBee.mp4
```

Download and run playvid immediately.

```
oldownload "https://www.youtube.com/watch?v=a6-MraffDlE" | % { playvid2 $_ }
```

Or use -p or --play option.

```
oldownload -p "https://www.youtube.com/watch?v=a6-MraffDlE"
```

# ugoira

1. PixivUtil2 の readme を読んでログイン可能である事を確認して下さい。
1. 設定は以下のように変更します。

```~/.local/pixivutil/config.ini
[Network]
useragent = Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0

[Settings]
writeImageJSON = True
writeImageInfo = True

[Authentication]
username = user_xxxx9999
password = XXXXXXXXXXXXXXX
cookie = 99999999_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

ugoira 形式のアニメーションのみ再生できます。
再生可能なうごイラは以下のものがあります。

- 49319675 まんぞくさんのフードファイト
- 46671388 miku 深海少女

https://www.pixiv.net/artworks/<ID> でブラウザで確認してください。

# LaserCube

実機 (LaserCube) で投影するには laserdock_jack.exe を使用します。
simulator を使用した場合と異なるのは laserdock_jack.exe を実行しておく必要があるのと output.exe を使用することです。 output.exe は映像の歪みなどを補正する事ができます。プロジェクターの台形補正と同じ様に LaserCube が投影する映像を補正するのに利用できます。

1. olstart で Jack Audio と simulator を起動します。
1. output を実行します。
1. LaserCube に電源を入れて PC と USB 接続します。
1. laserdock_jack を実行します。
1. qplayvid で動画を再生して投影します。

```
. "C:\Program Files\JACK2\qjackctl\qjackctl.exe"
start "C:\Program Files\openlase\bin\output.exe"
start "C:\Program Files\lasershark_hostapp\bin\laserdock_jack.exe"
qplayvid $HOME/.cache/openlase/bad_apple.mp4
```

# Pylase

OpenLase の python バインディングを使ったサンプルを実行します。

NOTE: Python3.8 以降は DLL 探索に環境変数 PATH を使用しません。pylase のロードの前に `os.add_dll_directory("C:\\windows")` とするか、jack.dll を `C:\Program Files\openlase-x.x.x\bin` にコピーします(読み込まれる pylase.cp311-win_amd64.pyd と同じディレクトリ)。

```
python "C:\Program Files\openlase\bin\simple.py"
```

# Programs

| name              | description                                                                                        |
|-------------------|----------------------------------------------------------------------------------------------------|
| cal               | フルカラーの円を映像出力。                                                                         |
| circlescope       | 音に反応して赤い円が変化する映像を出力。                                                           |
| demo              | BGM 付きの OpenLase のデモ。音声と同期した映像を出力する。                                         |
| harp              | レーザーで楽器（ハープ）を投影出力する。                                                           |
| harp.py           | カメラでレーザーをキャプチャして音階を奏でる (動作未確認)。                                        |
| harp2.py          | カメラでレーザーをキャプチャして音階を奏でる (動作未確認)。                                        |
| invert            | 入力を反転反転するツール。                                                                         |
| output            | GUIで入力された座標を変換して出力する為のツール。                                                  |
| playilda          | .ild ファイルを描画出力。                                                                          |
| playvid           | 動画をリアルタイムでトレースして音声と共に描画出力する。                                           |
| qplayvid          | playvid の GUI バージョン。                                                                        |
| scope             | リアルタイムに音に反応して赤い横線が変化する映像を描画出力。                                       |
| simple            | ２つの立方体が回転するアニメーションを描画出力。                                                   |
| simulator         | 描画出力を入力して画面上にレンダリングして表示するシミュレーター。                                 |
| kinect_shadows.py | kinect から得た画像をトレースしてリアルタイムで描画出力する (以前改造して動かしたがソースがない)。 |
| rect.py           | 単純な四角形のトレースを描画出力。                                                                 |
| showsvg.py        | SVG の描画出力。                                                                                   |
| simple.py         | simple.exe の python バージョン。                                                                  |
| svg.py            | showsvg で利用する python ライブラリ。                                                             |
| showtext.py       | 文字列の描画出力。                                                                                 |
| svg2ild.py        | .svg を .ild に変換する。                                                                          |
| tweet.py          | Twitter (旧X) のツイートを描画出力(たぶん)。                                                       |
| ugoira_player.py  | 旧 Pixiv 用のうごイラを描画出力。                                                                  |
| ugoira_player2.py | Pixiv のうごイラを描画出力。                                                                       |
| webcam_shadows.py | カメラの映像をリアルタイムで描画出力。                                                             |
