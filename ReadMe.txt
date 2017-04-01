CardWirthPy ver.2α4
===============================

作者
 : logの中の人
URL
 : http://sites.google.com/site/cardwirthpy/
 : https://bitbucket.org/k4nagatsuki/cardwirthpy-reboot (暫定)

このソフトは
--------------------------------------------------------------------------

GroupAskが開発したCardWirthの動作を再現・改良することを目的としたフリーのゲームソフトです。


仕様
--------------------------------------------------------------------------

次のOSで動作確認を行っています。

 * Windows XP(32bit)
 * Windows 7(64bit)

次のOSでは、以前動作確認していましたが現在は未保証です。

 * Windows2000(32bit)
 * Windows Vista(32bit)

いちおうマルチプラットフォーム化を視野に入れており、次のOSでもまれに動作確認を行っています。アップデートのたびの確認は行っていないのでご注意ください。

 * Linux Mint 14(64bit/32bit)

### サポートしている画像形式

BMP, JPG, PNG, GIF(non animated)

### サポートしている音楽と効果音形式

MIDI, WAV, MP3, OGG

吉里吉里形式及びRPGツクール形式の音声ループ情報に対応しています。

### サポートしているシナリオ圧縮形式

WSN, ZIP, CAB, LHA(lh1を除く)


操作方法
--------------------------------------------------------------------------

基本的な操作方法はCardWirthと同じです。

いくつかの機能にショートカットキーが割り当てられているので、以下に列挙しておきます。

Escape: 画面を右クリックした時と同じ。キャンセルや戦闘行動の開始、CardWirthPyの終了など
Shift: メッセージを一時的に非表示にする
F2: 設定ダイアログを開く
F3: デバッグモードの時、デバッガを開閉する
F4: 画面を拡大(またはフルスクリーン化)・縮小する
F5: メッセージログを表示する
F6: 情報カードを表示する。デバッグモードでのバトル中であれば同行キャストを表示する
F7: バトルの自動行動のオン・オフを切り替える
F9: シナリオからの緊急避難
PrintScreen または Ctrl+P: 画面のスクリーンショットを撮影する
Ctrl+D: デバッグモードのオン・オフを切り替える
Ctrl+C: 表示中のメッセージやメッセージログをコピーする

以下のマウス操作を行えます。

ホイール上回転: メッセージログを表示する
メッセージ表示中に右クリック: メッセージを一時的に非表示にする
右クリック+ホイール回転: 全体音量を変更する


CardWirthのデータの引継
--------------------------------------------------------------------------

CardWirthPyは、CardWirthの宿データ・シナリオデータをCardWirthPyであつかえるデータ(XML形式)に変換し、引き継いで利用することができます。

※ ver0.12.1からシナリオデータの変換は不要になりました。Scenarioフォルダ内のショートカットにも対応したため、移動させる必要もありません。

宿データは「宿の選択」ダイアログ、シナリオデータは「貼紙を見る」ダイアログにそれぞれデータフォルダをドラッグアンドドロップして変換してください。


シナリオエディタ
--------------------------------------------------------------------------

CWXEditorというエディタで、CardWirthPyのシナリオデータを作成・編集することができます。

 * [CWXEditor](https://bitbucket.org/k4nagatsuki/cwxeditor/)


CardWirthと違うところメモ
--------------------------------------------------------------------------

改良は多岐に渡って行われているため、この項の内容は「仕様が異なる」というレベルの事に絞って記述しています。

### データ形式について

 * CWPy形式のシナリオは"wsn"という拡張子の単一ファイル(ZIP形式で圧縮したファイルの拡張子をリネームしたもの)で管理。
 * バリアントの代わりにスキン方式を採用。CardWirthやそのバリアントからスキンを自動生成できる。
 * シナリオで得たカードを持ち帰る時、そのカードが使用する素材があればそれも一緒に持ち帰る。
 * カード1枚ごとにデータを保存。入手元シナリオ名や画像等が勝手に揃えられることがなく、そのまま記録される。

### インタフェースについて

 * レベル調節で手放したカードをレベルを戻した際に自動的に戻す機能。
 * Enterを押下し続けるとアニメーションも省略する。
 * バトル開始イベント中は右下に"Round 0"と表示する。

### デバッグ機能について

 * デバッグ宿と通常宿を区別せず、オプションでモードを切り替える。ユーティリティモードもデバッグモードに統合。

### CardWirthの問題の修正や互換性について

 * おおよそCardWirth 1.20～1.50までで互換性が失われている部分に対して互換モードで動く機能を追加。互換性データベースを用意し、互換性問題のある既知のシナリオは自動的に互換モードで動く。
 * FPSの概念を持ち、セルアニメ等はほぼ確実にFPS 30で動く。
 * CardWirth 1.28以前の動画再生に対応。
 * 効果コンテントによる効果を回避した場合には無効果音ではなく回避音が鳴る。
 * 長いカード名や選択肢は横幅に合わせて縮小する。
 * エフェクトブースターの実行中もほとんどの操作を受け付ける。
 * CardWirthではエフェクトブースターの一時描画をF9で飛ばせるが、CardWirthPyではEnterの長押しでウェイトを省略できる。アニメーション中でもF9の機能は従来のままとなる。

### CardWirthにはあるがCardWirthPyには無い機能

 * CardWirthの宿データをそのまま読み込む機能。必ず変換が必要です。技術的問題が多いため、今のところ変換無しで遊べるようにする予定はありません(変換→逆変換によって宿データのやり取りをする事は可能です)。
 * ヘルプ。まだありません。
 * スクリーンショットの撮影にダイアログが含まれません。将来のバージョンで改善されるかもしれません。
 * デバッグ宿でのキーコード表示。0.12.2以降で、表示のみならずイベントを直接実行する機能の実装を考えています。
 * その他CardWirthNextの新機能。事情により対応できません。


エラーが出たとき
--------------------------------------------------------------------------

CardWirthPyには現在のところ未完成の機能はありませんが、完成度という点ではまだ道半ばです。

不可解なエラーでプログラムが機能しなかった場合は、"CardWirthPy.exe.log"に記されているエラーログを添えて開発者までお知らせください。

### 既知の不具合について

#### 音声の不具合

環境によって、音声の再生で問題が発生することがわかっています。次のような問題が、サウンドフォントが存在しないか、サウンドフォントをまったく使用しない設定になっている時に発生します。

 * BGMの終了時に時々ハングアップする。
 * サウンドフォントを使用する設定から使用しない設定にした時にハングアップする。
 * 音声ファイルの形式によっては音量調節や再生可否の設定が機能しない。

このような問題が発生する場合、標準のサウンドフォントを使用するように設定を変更してください。

#### シナリオ読込の不具合

シナリオが存在するにも関わらずシナリオ選択ダイアログに表れず、表れたシナリオも読み込みに失敗する状態になることがあるようです。この問題が発生した場合は、`CardWirthPy.exe`と同じフォルダにある`Scenario.db`を削除して再起動してください。

#### ダイアログの不具合

ダイアログのボタンにフォーカスがある時に`Ctrl+D`などのキー操作を行うとWindowsの警告音が鳴ることが分かっていますが、解決できていません。警告音が鳴る以外の実害はありません。


互換モード
--------------------------------------------------------------------------

シナリオを CardWirth の過去のバージョン相当の環境で再生する事ができます。例えば1.28以降ではプレイヤーカードがメニューカードより前に描画されますが、1.20モードで動かす事により、(CardWirth 1.20のように)その順序を逆にする事ができます。互換モードを有効にするには、次の二つの方法があります。

### mode.ini

シナリオフォルダの直下に"mode.ini"を追加する。"mode.ini"の内容は以下のようにしてください。

    [Compatibility]
    engine=1.28

項目"engine"の値に、そのシナリオを再生すべきCardWirthエンジンのバージョンを記述します。例えば1.20相当の動作をさせたい場合は以下のようにします。

    [Compatibility]
    engine=1.20

メニューカードをプレイヤーカードより前に表示する設定のみ有効にしたい場合は次のようにします。

    [Compatibility]
    zIndexMode=1.20

パーティメンバが再配置される前にシナリオを終了すると対象消去されたメンバが戻ってくるバグを利用する場合は次のようにします。

    [Compatibility]
    enableVanishMemberCancellation=true

### 互換性データベース

互換性データベースにシナリオの情報を追加する。作者に、互換性の問題でプレイできない過去のシナリオの情報を伝えてください。それについて確認できれば、シナリオの情報を互換性データベースに登録する事により、あらゆるプレイヤーがそのシナリオを妥当な互換モードでプレイできるようになります。

### 互換モードに関する注意

これらはあくまで互換性のために用意されている機能であり、これらの機能に依存したシナリオを作成する事は非推奨です。


CardWirthPyでプレイ中か判定するイベントを作る方法について
--------------------------------------------------------------------------

※ この項の内容はシナリオ作者向けです。

理想的には、シナリオ作者はエンジンのバージョンを気にせずにシナリオを作れるべきです。特に、CardWirthPyには、過去に作られたシナリオが可能な限り正しく動くよう、互換モードが搭載されています。本来ならば、シナリオにCardWirthPyのどのバージョンでプレイ中かなどといった判断を入れる必要はありません。

しかし、些細と見なされた仕様の違いやバグなどに引っかかってシナリオが正しく動かなくなるような事態は、どうしても稀に発生するものと思われます。そこで、CardWirthPy 0.12.2以降では、称号所持分岐によって、プレイヤーがCardWirthPyを使用中か、使用中であればどのバージョンであるかを判別できるようになりました。

バージョン2現在、称号所持分岐で、次の2つの称号の所持判定は、実際に所持しているかどうかによらず必ず成功します。

 * ＠CardWirthPy Version.2.0
 * ＠CardWirthPy Version.2.0 Only

このうち、「Only」がついている称号は、CardWirthPyのバージョンアップ時に削除され、新しいバージョン固有の称号に差し替えられます。「Only」がついていない称号は、バージョンアップ後も残ります。

CardWirthPyでプレイ中か判定する時やバージョンが2以降であるか判定する時には、「＠CardWirthPy Version.2.0」を使用して称号判定分岐を行ってください。

CardWirthPy 2固有で将来修正される見込みのバグに対処したい場合などは、「＠CardWirthPy Version.2.0 Only」を使用してください。

使用可能な過去のバージョンの称号のリストは以下の通りです。

 * ＠CardWirthPy Version.0.12.2
 * ＠CardWirthPy Version.0.12.3
 * ＠CardWirthPy Version.0.12.3b
 * ＠CardWirthPy Version.1.0
 * ＠CardWirthPy Version.1.1
 * ＠CardWirthPy Version.2.0


WSN形式の特定バージョンへの対応を示すクーポンについて
--------------------------------------------------------------------------

「WSN形式」とは、CardWirthPyが再生できるCardWirthシナリオのデータ形式の一つです。現時点ではCardWirthPy独自のデータ形式ですが、将来は他のCardWirthエンジンでも再生可能となる事を前提として、オープンな場で設計されています。

WSN形式のバージョンの一つである「Wsn.2」では、対応するCardWirthエンジンが、称号判定分岐で`＠Wsn.2`というシステムクーポンの所持判定を行った時、実際に所持しているかいないかに関わらず必ず成功させるように求めています。従って、CardWirthPy 2はそのように動作します。

`＠Wsn.2`による判定を行えば、現在プレイヤーが使用しているCardWirthエンジンが「Wsn.2」に対応しているかどうかを、シナリオ側から知る事が可能です。


ライセンス
--------------------------------------------------------------------------

CardWirthPyはプログラミング言語Pythonで書かれました。実行ファイルの作成にはpy2exeを使用しています。

[Python ver2.7.13 (32bit版)](http://www.python.org/)
 : License: Python Software Foundation License

[py2exe ver0.6.9](http://www.py2exe.org/)

CardWirthPyは以下のPythonの外部モジュールを使用しています。

[wxPython ver3.0.2.0](http://www.wxpython.org/)
 : License: wxWindows Library License

[pygame ver1.9.2](http://www.pygame.org/)
 : License: GNU Lesser General Public License

[Python for Windows extensions Build 220](http://sourceforge.net/projects/pywin32/)
 : License: Python Software Foundation License

[lhafile 0.1](http://trac.neotitans.net/wiki/lhafile)
 : License: 修正BSDライセンス

CardWirthPyは以下のMicrosoftのライブラリを同梱しています。

[gdiplus.dll](http://www.microsoft.com/downloads/details.aspx?familyid=6A63AB9C-DF12-4D41-933C-BE590FEAA05A&displaylang=en)
 : License: Microsoft Redistributable

msvcp90.dll, msvcr90.dll
 : [Download](http://www.microsoft.com/japan/msdn/vstudio/)
 : License: Visual Studio 2008 Redistributable Code

CardWirthPyは一般利用者向けIPAフォントを同梱しています。

Data/Font/gothic.ttf, mincho.ttf, uigothic.ttf, pgothic.ttf, pmincho.ttf
 : [Web Site](http://ossipedia.ipa.go.jp/ipafont/)
 : License: 一般利用者向けIPAフォント エンド・ユーザ・ライセンス

CardWirthPyは音声再生用に以下のライブラリを同梱しています。これらはソフトウェアを無償配布する限りは自由に使用できますが、商用利用する場合は商用ライセンスを購入する必要があるのでご注意ください。

bass.dll, bassmidi.dll, bass32.so, bassmidi32.so, bass64.so, bassmidi64.so
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

"src.zip"に同梱しているプログラミングコードの著作権は作者が保持し、以下のライセンスが適用されます。

[The MIT License](http://www.opensource.org/licenses/mit-license.php)

CardWirthPyの実行形式には以下のライセンスが適用されます。

[GNU Lesser General Public License](http://www.gnu.org/copyleft/lesser.html)

各ライセンスの条文は、"License.txt"を参照してください。

同梱しているスキンデータの取り扱いについては、個別に、"Data/Skin"の各スキンフォルダにある"ReadMe.txt"を参照してください。


貢献者
--------------------------------------------------------------------------

ここにはコードやデータを直接寄贈した方のみ掲載しています。この他にも多くの方から、テスト・バグ報告・提案などで貢献していただいているため、これは完全なリストではない事をお断りしておきます。

名前のあとの「@...」は、[Bitbucket](https://bitbucket.org/)のユーザIDです。

(順不同・敬称略)

https://sites.google.com/site/cardwirthpy/
 : CardWirthPyは logの中の人 によって作成され、ほとんどの主要なコードは原作者によって書かれました。

https://bitbucket.org/k4nagatsuki/cardwirthpy-reboot
 : k4nagatsuki(@k4nagatsuki) は開発が停止していたCardWirthPyをフォークし、その時点で未完成だった部分のほとんどを実装しました。

https://bitbucket.org/takuto_cw/cardwirthpy-reboot
 : takuto_cw(@takuto_cw) はいくつかのバグを修正し、カードダイアログのボタンに使用する画像を描き起こしました。
 : また、レベル調節でのカードの移動やレベル変化時のEPの扱いなど、新機能や仕様についての具体的な提案や実装を行なっています。

https://bitbucket.org/tachi_gigas/cardwirthpy-reboot-lessor
 : TachiGigas(@tachi_gigas) はいくつかのバグを修正し、シナリオダイアログの見逃されていた未実装部分を実装しました。
 : また、フォント設定の提案と最初の実装、「冒険の再開」ダイアログでの先頭メンバ表示、所持カード一覧の撮影など、いくつもの機能の提案や実装を行っています。

Ganma Shadow(@GanmaShadow) は、いくつかの問題の報告を行った他、プレイヤーキャラクターの自動生成機能を提案し、Modern・School・Oedo・Monstersの各スキンタイプ向けに名前のリストを提供しました。

https://bitbucket.org/akkw/cardwirthpy-reboot
 : 暗黒騎士(@akkw) は、スキン「JUDGMENT」の作者です。
 : バグの報告、CardWirthとの仕様の食い違いの指摘と調査などに加え、それらの問題の解消作業や、荷物袋からのカード使用に関するオプション、ボタンの連続押し機能などの実装を行いました。
 : また、ファンタジーⅠ型やSFバリアント向けの名前のリストの提供も行っています。

ハルキゲニア(@tekitoudesu) は、全てのWsn.2標準効果音の作者です。また、音声再生に関する問題の報告・提案を多数行い、付属のサウンドフォント`TimGM6mb.sf2`の65:AltoSax (TB)のE4のノートに音が設定されていない事を指摘して修正しました。

https://irakat.bitbucket.io/
 : Iraka.T(@IrakaT) は、スキン「BloodWirth」の作者です。
 : CardWirthPy本体に対しても、いくつもの提案やバグ報告を行い、自ら修正も行っています。

http://misica.lv9.org/
 : みしか は、付属のサウンドフォント`TimGM6mb.sf2`の79:Whistleの発音でノイズの発生と音程の狂いが生じる問題を修正しました。

https://bitbucket.org/namereq/
 : name.req(@namereq) は、ランダム多岐分岐コンテントやクーポン分岐の複数称号対応化の実装者です。

http://www.geocities.jp/handmademidis/
 : HAND(@hand_cw) は、テキストセルの描画をCardWirth 1.50に合わせる修正を行いました。
 : Webサイトで公開されている、CardWirthの仕様に関する多くの検証結果と推察は、CardWirthPyの仕様の決定に大きく寄与しています。


謝辞
--------------------------------------------------------------------------

(順不同)

CardWirthPyを開発するにあたって、お世話になった方々に、心から感謝申し上げます。

[groupAsk様](http://www.ask.sakura.ne.jp/)

[カードワース愛護協会](http://cardwirth.net/)および書類の谷様

[どうせモテないしカードワースシナリオ作ろうぜスレの方々](http://hideyoshi.2ch.net/motenai/)

[Thomas様](http://thomascw.hp.infoseek.co.jp/)

[wanderer7様](http://wanderer7.hp.infoseek.co.jp/cw/)

[古山シウ様](http://hp.vector.co.jp/authors/VA016101/)

[CW GURU](http://hp.vector.co.jp/authors/VA016101/cwguru/)の投稿者の方々

[gulafu様](http://www.geocities.co.jp/Playtown/7299/cw/)

[CardWirth Skill Wiki](http://www9.atwiki.jp/cwskill/)の管理人様

[きりう様](http://homepage3.nifty.com/kiryu/cg/garden/jpy.html)

[HAND様](http://www.geocities.jp/handmademidis/)

その他、バグ報告・仕様提案などご意見くださったすべての方々
