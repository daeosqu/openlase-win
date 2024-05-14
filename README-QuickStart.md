# QuickStart

スタートメニューから openlase を起動します。Unix または Msys の場合は以下のように /usr/local/openlase/bin/openlase.sh をロードします。

OpenLase-win を利用する場合は毎回実行する必要があります。

## Windows

```
"C:\Program Files\openlase\bin\openlase.cmd"
```

## MinGW

```
. /ucrt64/local/openlase/bin/openlase.sh
```

## Unix

```
. /usr/local/openlase/bin/openlase.sh
```

# Setup

```
pip3 install -r requirements.txt
```

# OpenLase-win の開始

```
olstart
```

QjackCtl の Patchbay で config/openlase-laserdock.xml をロードしてアクティブ化します。オプションで Activate Patchbay persistence にチェックを入れて config/openlase-laserdock.xml を指定しておきます。

# simple

```
simple
```

# Bad Apple

```
oldownload "https://www.nicovideo.jp/watch/sm8628149"
playvid (Get-Item $env:OL_DATA_DIR\media\*Bad_Apple*Shadow*.mp4)
```

# Bad Apple (Color)

```
oldownload "uOyaCOViAPA"
playvid2 (Get-Item $env:OL_DATA_DIR\media\*Bad_Apple*Color*.mp4)
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
| ugoira_player.py  | Pixiv のうごイラを描画出力(動作せず)。                                                             |
| webcam_shadows.py | カメラの映像をリアルタイムで描画出力。           
