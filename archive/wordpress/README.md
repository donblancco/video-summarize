# WordPress記事自動投稿ツール

HTMLファイルからWordPressに記事を自動投稿し、YouTube動画との連携機能を提供するPythonスクリプトです。

## 🎯 主な機能

- **HTML記事の自動投稿**: HTMLファイルをWordPressの下書きとして自動投稿
- **YouTube連携**: ファイル名からYouTube IDを自動抽出し、サムネイル画像を設定
- **インタラクティブサムネイル**: クリック可能なサムネイル画像（YouTube動画へリンク）
- **スタイリッシュなUIボタン**: モダンなデザインのYouTubeリンクボタン
- **フッター結合**: 追加HTMLファイルの自動結合機能

## 📋 前提条件

### システム要件
- Python 3.7+
- WordPress 4.7+（REST API対応）
- インターネット接続

### WordPressの設定
1. **Application Password**の作成
   - WordPress管理画面 → ユーザー → プロフィール
   - 「Application Passwords」セクションで新しいパスワードを生成

2. **必要な権限**
   - 投稿の作成・編集権限
   - メディアのアップロード権限

## 🚀 セットアップ

### 1. 依存パッケージのインストール
```bash
pip install requests beautifulsoup4
```

### 2. スクリプトの設定
`wordpress_test.py`内の設定を編集：
```python
SITE_URL = "https://your-wordpress-site.com"
USERNAME = "your_username"
APP_PASSWORD = "xxxx xxxx xxxx xxxx xxxx xxxx"
```

## 📁 ファイル命名規則

HTMLファイルは以下の命名規則に従ってください：
```
article_[YOUTUBE_VIDEO_ID]_[DATE]_[TIME].html
```

**例:**
- `article_pyPfHTfVcqU_20250719_144238.html`
- `article_dQw4w9WgXcQ_20250720_120000.html`

## 💻 使用方法

### 基本的な投稿
```bash
python wordpress_test.py article_pyPfHTfVcqU_20250719_144238.html
```

### フッターHTMLファイル付きで投稿
```bash
python wordpress_test.py article.html footer.html
```

### 絶対パスでの指定
```bash
python wordpress_test.py "/path/to/article.html" "/path/to/footer.html"
```

## 🎬 YouTube連携機能

### 自動処理内容
1. **ファイル名解析**: YouTube ID（`pyPfHTfVcqU`）を自動抽出
2. **サムネイル取得**: `https://img.youtube.com/vi/{ID}/maxresdefault.jpg`
3. **メディアアップロード**: WordPressメディアライブラリに保存
4. **アイキャッチ設定**: 投稿のfeatured_mediaに自動設定

### 生成される要素
- **クリック可能サムネイル**: 中央に再生ボタン表示
- **YouTubeリンクボタン**: 記事末尾にスタイリッシュなボタン
- **ホバー効果**: アニメーション付きの視覚的フィードバック

## 🎨 UI/UX機能

### サムネイル画像
- 中央に再生ボタン（▶）アイコン
- ホバー時のズーム・透明度変化
- クリックでYouTube動画を新しいタブで開く

### YouTubeリンクボタン
- グラデーション背景（YouTube風カラー）
- ホバー時の浮き上がり効果
- クリック時の押し込みアニメーション

## ⚙️ 設定詳細

### 固定設定
```python
status = "draft"          # 常に下書きとして投稿
category_id = 17          # 施術動画カテゴリー
```

### カスタマイズ可能な項目
- 追加HTMLファイルのパス
- YouTubeボタンのテキスト
- CSSスタイル（色、サイズ、アニメーション）

## 🔧 トラブルシューティング

### よくある問題

#### 1. 接続エラー
```
❌ WordPress API接続失敗
```
**解決策:**
- サイトURLの確認（https://含む）
- Application Passwordの再生成
- ファイアウォール設定の確認

#### 2. ファイルが見つからない
```
❌ HTMLファイルが見つかりません
```
**解決策:**
- ファイルパスの確認
- 現在のディレクトリの確認
- ファイル存在の確認

#### 3. サムネイルアップロード失敗
```
⚠️ サムネイルアップロードに失敗
```
**解決策:**
- インターネット接続の確認
- YouTube IDの正確性確認
- WordPressメディア権限の確認

### デバッグ情報の確認
スクリプト実行時に以下の情報が表示されます：
- 使用ファイル情報
- YouTube ID検出状況
- アップロード進行状況
- 投稿結果（ID、URL、編集リンク）

## 📊 出力例

```
使用するHTMLファイル: article_pyPfHTfVcqU_20250719_144238.html
追加HTMLファイル: footer.html
🎥 ファイル名からYouTube IDを検出: pyPfHTfVcqU
✅ WordPress API接続成功
📥 YouTubeサムネイルをダウンロード中: https://img.youtube.com/vi/pyPfHTfVcqU/maxresdefault.jpg
📤 WordPressメディアライブラリにアップロード中...
✅ YouTubeサムネイルをアップロードしました
   メディアID: 123
   URL: https://example.com/wp-content/uploads/youtube_pyPfHTfVcqU_title.jpg

=== 投稿データ ===
タイトル: 【要注意】フィナステリドでは"生えない"!? 医師が語る本当に必要な治療とは
ステータス: draft
カテゴリー: 施術動画 (ID: 17)
本文の長さ: 12543 文字
アイキャッチ画像: メディアID 123

投稿を実行しています...

=== 投稿成功 ===
投稿ID: 456
投稿URL: https://example.com/?p=456
編集URL: https://example.com/wp-admin/post.php?post=456&action=edit
🖼️ アイキャッチ画像: YouTubeサムネイル (メディアID: 123)
   → <figure class="p-single__thumb"> にYouTubeサムネイルが表示されます
```

## 🛠️ 技術仕様

### 使用技術
- **Python 3.7+**
- **WordPress REST API**
- **BeautifulSoup4**: HTML解析
- **Requests**: HTTP通信
- **CSS3**: アニメーション・レスポンシブデザイン
- **Vanilla JavaScript**: DOM操作・イベント処理

### API仕様
- **投稿API**: `POST /wp-json/wp/v2/posts`
- **メディアAPI**: `POST /wp-json/wp/v2/media`
- **認証方式**: Basic認証（Application Password）

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🤝 コントリビューション

プルリクエスト、イシューの報告、機能提案を歓迎します。

### 開発に参加する場合
1. リポジトリをフォーク
2. 機能ブランチを作成
3. 変更をコミット
4. プルリクエストを作成

## 📞 サポート

問題や質問がある場合は、GitHubのイシューページで報告してください。

---

**開発者**: Claude & Human Collaboration  
**最終更新**: 2025年7月19日