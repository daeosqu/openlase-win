# README-MinGW

## Requirements

- Windows 11
- Msys2
  - git
- [JACK 1.9.22 win64](https://github.com/jackaudio/jack2-releases/releases/download/v1.9.22/jack2-win64-v1.9.22.exe) JACK Audio Connection Kit for Windows 64bit
- [laserdock_jack](https://github.com/daeosqu/laserdock_jack.git)

## Prepare

スタートメニューから MSYS2 UCRT64 を起動して必要なパッケージをインストールします。

Msys2 システムを更新します。複数回行う必要がある場合があります。

```
pacman -Syuu
pacman -S --noconfirm git
```

git の改行変換を無効にします。

```
git config --global core.autocrlf false
```

## Clone

```
cd
git clone https://github.com/daeosqu/openlase-win.git
echo 'OL_DEVEL=1' > .env
```

## Build and Install

```
cd $HOME/openlase-win
export OL_DEVEL=1
. openlace-dev.sh
python -m pip install -r requirements.txt
olbuild
olinstall
```
