Mac版ビルド情報
===============

必要環境
--------

* Xcode
* autoconf-2.59 or later
* pkg-config
* XQuartz
* pip, virtualenv

どのパッケージもよほど古くない限り大丈夫だと思います。autoconf と
pkg-config は、自力で入れても、fink や macports で入れても OK です。

手元のビルド環境は以下の通りです。

* Xcode 9.0
* autoconf 2.69   (fink にてインストール)
* pkg-config 0.28 (fink にてインストール)
* XQuartz 2.7.11
* pip 9.0.1, virtualenv 15.1.0


ビルド手順
----------

このディレクトリで作業します。
初回のライブラリのビルド時に Internet からライブラリのアーカイブを
ダウンロードするので、Internet 接続環境が必要です。

```
$ ./build_alllibs.sh
$ ./build_app.sh
```

親ディレクトリに `CardWirthPy.app` が出来ます。さらに、

```
$ ./create_dmg.sh
```
とすると、配布用の dmg ファイルが出来ます。

尚、`./build_alllibs.sh` のみだと、このディレクトリに python
virtualenv 環境が出来ます。app を作らずに CardWirthPy のデバッグが
したい場合は、
```
$ . bin/activate
$ cd ..
$ python cardwirth.py
```
でコマンドラインから実行できます。

その他
------

* エラーチェックなどは最低限しかしていません。  
  一応ダウンロードしたアーカイブが壊れていないかを sha1 digest で
  チェックしています。

* パッチ等大歓迎です。


mac ビルド環境 & パッチ作成者
-----------------------------

* MURAMATSU Atsushi (@amuramatsu) <amura@tomato.sakura.ne.jp>  
  amuramatsu が作成したビルド環境は、全て CardWirthPy と同じ MIT
  ライセンスとします。  
  各パッチについては、パッチ先のライセンスに従います。詳細は、
  "patches/LISENCE_patch.md" をご覧ください。

