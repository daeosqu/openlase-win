# README-netjack

ネットワーク経由で Jack Audio を使用する方法について解説します。
Windows と WSL 間で動作確認しました。ただし、再生に遅延が発生し、再生速度に乱れがありました。

# 前提

- Windows および Linux または WSL で通常の再生が可能である事。

1. QJackCtl を起動した状態である事を確認します。
1. netmanager をロードします。
   ```powershell
   &"C:\Program Files\JACK2\tools\jack_load.exe" netmanager -i -c
   ```

## WSL での操作

次に WSL で IP アドレスを確認します。

Jackd を起動します。

```
olstart_slave
```

または

```
WSL_IP=$(sed -ne 's,^\s*nameserver\s*\(.*\)$,\1,p' /etc/resolv.conf)
jackd -d net -a $WSL_IP -n olnet -C 7 -P 7 &
jack_wait -w
run_qjackctl --active-patchbay "$OL_DIR/config/openlase-netjack.xml"
```

QJackCtl を起動して Patchbay で config/openlase-netjack.xml をロードしてアクティブにします。

再生します。

```
playvid /mnt/c/opt/el/data/bad_apple.mp4
```

"$OL_DIR/config/openlase-netjack.xml"
