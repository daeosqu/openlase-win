# Install for Linux

Ubuntu (WSL) でのビルド方法について解説します。

# Clone

```
cd $HOME
git clone https://github.com/daeosqu/openlase-win.git
```

# Build

```
cd $HOME/openlase-win
. openlase.sh
python -m pip install -r requirements.txt
olbuild
olinstall
```

# Setup PulseAudio

WSL 以外の Unix 系 OS で Pulseaudio を利用している場合は以下のようにして PulseAudio を Jack から認識できるように構成する事が出来ます(要確認)。

```
pactl load-module module-jack-sink channels=2
pactl load-module module-jack-source channels=2
```

# WSL2

WSL2 (Ubuntu22) でのセットアップ方法について解説します。

## jack-over-pulseaudio

WSL2 の場合は WSLg がネイティブで PulseAudio をサポートしています。ただし pactl load-module を使うことが出来ないのでドライバーに dummy を使用してjack-over-pulseaudio を使って PulseAudio にブリッジする事で Jack Audio 経由でオーディオを Windows で再生する事ができます。WSL の場合は ninja install で jopa が /usr/local/bin にインストールされます。

## freeglut のエラーについて

simulator を起動したときに以下のようなエラーが発生した場合は環境変数 LIBGL_ALWAYS_INDIRECT がセットされている場合は空にするか unset してください。

```
freeglut (simulator): Unable to create OpenGL 1.0 context (flags 0, profile 0)
```

```
LIBGL_ALWAYS_INDIRECT= simulator
```

または

```
unset LIBGL_ALWAYS_INDIRECT
simulator
```

## jack-over-pulseaudio のビルド

```
sudo apt install libpulse-dev
git clone https://github.com/m13253/jack-over-pulseaudio.git
cd jack-over-pulseaudio
make
```

## jopa の実行

jopa を実行すると Jack Audio から PulseAudio にオーディオをバイパスする事ができます。

```
./jopa
```
