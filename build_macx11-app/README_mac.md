Mac版について
=============

これは何
--------

logの中の人 氏が作成し、現在 k4nagatsuki 氏が中心となって開発を継
続している CardWirth 互換環境「 **CardWirtyPy** 」を、 macOS（旧
称 OS X or Mac OS X）で動作するようにビルド、パッケージ化した物で
す。

残念ながら、技術的な理由から、macOS の標準 UI である Cocoa UI では
ありませんが、ひとまず mac で CardWirth を遊ぶことが出来ます。


動作必要要件
------------

* OS X / macOS Mavericks (10.9) or later  
  Lion (10.7) あたりから動作する気はしますが、動作確認環境がないた
  めサポート出来ません。


* 64bit 対応の Intel CPU を搭載した Macintosh  
  （Early 2006 の iMac、MacBook、MacBook pro、
    Early/Late 2006 Mac mini は残念ながら 64bit サポートがないため
    動作しません）

* [XQuartz](https://www.xquartz.org)  
  どのバージョンから動くか分かりませんが、少なくとも 2.7.11 なら動
  作します。


インストール
------------

事前に、 [XQuartz](https://www.xquartz.org) のインストールが必要で
す。XQuartz の最新版をダウンロードして、インストールしてください。

実行ファイル `CardWirthPy.app` を、CardWirthPy の Data、Scenario、
Yado フォルダがある場所に置きます。一番簡単なのは、windows 版の
CardWirthPy fullpack をダウンロードして展開し、
`CardWirthPy.exe` がある場所に `CardWirthPy.app` を置くことです。

後は、 `CardWirthPy.app` をダブルクリックして実行すれば、
**CardWirth** を楽しめます。

# Skin、シナリオの追加について

Skin、シナリオの追加方法は、 windows 版と同じです（なんたる手抜き
説明）

ただし、 **Drag & Drop は未テストですので、動かない可能性が高い**
です。

# Yado などの windows 版との共用

ファイルフォーマットなどは同一なので、何もせずに共用できるはずです
が、PC 名や宿名に濁点、半濁点が入っているとおかしくなる可能性があ
ります。（ファイル名の扱いに違いがあるためです）

できるだけ共用しない方が良いでしょう。


制限事項
--------

以下の制限事項があります。特に、
**制限事項 1. 2. 3. については、近い将来に改善する予定はありません。** 
CardWirtyPy を全面的に書き換えないと修正できないためです。

1. 動作に [XQuartz](https://www.xquartz.org) が必要です。  
   技術的な理由により、 Cocoa API では動作出来なかったためです。
2. 1. に付随して、 **IMを使用した日本語の入力は出来ません。**  
   日本語の copy & paste は出来ますので、宿名や PC 名などで日本語
   を入れたいときは、 TextEdit 等に日本語を打ち込んで、コピペして
   ください。
3. Retina ディスプレイでも高解像度表示にならない。  
   これも 1. による弊害です。
4. 動作がもっさりしています。  
   チューニング不足です。そのうち改善したいです。
5. チェック不足。  
   手元にあるいくつかの環境でしか動作確認出来ていません。
   動作報告/障害などいただけると幸いです。


動作確認環境
------------

現在、以下の 3 つで動作確認しています。

* （開発マシン）MacBook pro 13-inch with Touch bar, Late 2016,
  macOS Sierra (10.12.6), XQuartz 2.7.11

* MacBook pro 13-inch, Early 2010,
  OS X El Capitan (10.11.6), XQuartz 2.7.11

* VMware Fusion 8.5.8 @(MacBook pro 13-inch with Touch bar, Late 2016),
  OS X Mavericks (10.9.5), XQuartz 2.7.11


mac ビルド環境 & パッチ作成者
-----------------------------

* MURAMATSU Atsushi (@amuramatsu) <amura@tomato.sakura.ne.jp>  
  amuramatsu が作成したビルド環境は、全て CardWirthPy と同じ MIT
  ライセンスとします。


ACKNOWLEDGEMENTS
----------------

* This software is based in part on the work of the Independent
  JPEG Group.  
  このソフトウェアは、Independent JPEG Group の成果を含んでいます。


ライセンス
----------

CardWirthPy.appはプログラミング言語Pythonで書かれました。実行ファ
イルの作成にはpy2appを使用しています。

[py2app ver0.14](https://bitbucket.org/ronaldoussoren/py2app)

CardWirthPy.appは以下のPythonの外部モジュールを使用しています。

[wxPython ver3.0.2.0](http://www.wxpython.org/)
 : License: wxWindows Library License

[pygame ver1.9.3](http://www.pygame.org/)
 : License: GNU Lesser General Public License

[lhafile 0.1](http://trac.neotitans.net/wiki/lhafile)
 : License: 修正BSDライセンス

CardWirthPy.appは以下のライブラリが含まれています。

[libjpeg 9b](http://ijg.org)
 : License: IJG's JPEG software ライセンス

[libpng 1.6.32](http://www.libpng.org/pub/png/libpng.html)
 : License: libpng ライセンス

[tiff 4.0.8](http://www.simplesystems.org/libtiff/)
 : License: libtiff ライセンス (MIT style License)

[SDL 1.2.15](https://www.libsdl.org/index.php)
 : License: GNU Lesser General Public License

[SDL_image 1.2.12](https://www.libsdl.org/projects/SDL_image/release-1.2.html)
 : License: GNU Lesser General Public License

[SDL_mixer 1.2.12](https://www.libsdl.org/projects/SDL_mixer/release-1.2.html)
 : License: GNU Lesser General Public License

[SDL_ttf 2.0.11](https://www.libsdl.org/projects/SDL_ttf/release-1.2.html)
 : License: GNU Lesser General Public License

[gettext 0.19.8.1](https://www.gnu.org/software/gettext/)
 : License: GNU General Public License
   ただしCardWirthPy.appに含まれるlibintl.dylibは
            GNU Lesser General Public License

[glib 2.54.0](https://wiki.gnome.org/Projects/GLib)
 : License: GNU Lesser General Public License

[harfbuzz 1.5.1](http://harfbuzz.org)
 : License: MIT License

[pango 1.6.32](http://www.pango.org)
 : License: GNU Lesser General Public License

[atk 2.24.0](https://wiki.gnome.org/Accessibility)
 : License: GNU Lesser General Public License

[gdk-pixbuf 2.36.10](https://git.gnome.org/browse/gdk-pixbuf/)
 : License: GNU Lesser General Public License

[gtk+ 2.24.31](https://www.gtk.org)
 : License: GNU Lesser General Public License

CardWirthPy.appは一般利用者向けIPAフォントを同梱しています。

Data/Font/gothic.ttf, mincho.ttf, uigothic.ttf, pgothic.ttf, pmincho.ttf
 : [Web Site](http://ossipedia.ipa.go.jp/ipafont/)
 : License: 一般利用者向けIPAフォント エンド・ユーザ・ライセンス

CardWirthPy.appは音声再生用に以下のライブラリを同梱しています。こ
れらはソフトウェアを無償配布する限りは自由に使用できますが、商用利
用する場合は商用ライセンスを購入する必要があるのでご注意ください。

bass.dylib, bassmidi.dylib
 : [Web Site](http://www.un4seen.com/)
 : License: BASS Audioのライセンス

CardWirthPyは"CWXEditor"のリソースの画像ファイルを一部改変して同梱しています。

Data/Debugger にあるすべての画像ファイル
 : [CWXEditor](https://bitbucket.org/k4nagatsuki/cwxeditor/)
 : License: Public Domain

Data/SkinBase 以下にあるすべての画像及び音声ファイル
 : CWXEditorからの流用か、CardWirthPy用に作成されたものです。
 : "Sound/System_ScreenShot.wav"は、CardWirth 1.50のパッケージに含まれるPublic Domainのファイル"システム・スクリーンショット.wav"を流用したものです。
 : License: Public Domain

CardWirthPy.app全体には以下のライセンスが適用されます。

[GNU Lesser General Public License](http://www.gnu.org/copyleft/lesser.html)

各ライセンスの条文は、"LICENSE_mac.txt"を参照してください。
