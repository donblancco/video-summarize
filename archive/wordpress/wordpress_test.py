import requests
import json
import base64
from bs4 import BeautifulSoup
import os
import sys

class WordPressAPITester:
    def __init__(self, site_url, username, app_password):
        """
        WordPress API テスター
        
        Args:
            site_url (str): WordPressサイトのURL (例: https://example.com)
            username (str): WordPressユーザー名
            app_password (str): Application Password
        """
        self.site_url = site_url.rstrip('/')
        self.api_url = f"{self.site_url}/wp-json/wp/v2"
        self.username = username
        self.app_password = app_password
        
        # Basic認証のヘッダーを作成
        credentials = f"{username}:{app_password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json'
        }
    
    def get_categories(self):
        """カテゴリー一覧を取得"""
        try:
            response = requests.get(f"{self.api_url}/categories", headers=self.headers)
            response.raise_for_status()
            categories = response.json()
            
            print("=== 利用可能なカテゴリー ===")
            for cat in categories:
                print(f"ID: {cat['id']}, 名前: {cat['name']}, スラッグ: {cat['slug']}")
            
            return categories
        except requests.exceptions.RequestException as e:
            print(f"カテゴリー取得エラー: {e}")
            return []
    
    def find_category_by_name(self, category_name):
        """カテゴリー名からIDを取得"""
        categories = self.get_categories()
        for cat in categories:
            if cat['name'] == category_name:
                return cat['id']
        
        print(f"カテゴリー '{category_name}' が見つかりません")
        return None
    
    def create_category(self, category_name):
        """新しいカテゴリーを作成"""
        try:
            data = {
                'name': category_name,
                'slug': category_name.lower().replace(' ', '-')
            }
            
            response = requests.post(
                f"{self.api_url}/categories", 
                headers=self.headers,
                data=json.dumps(data)
            )
            response.raise_for_status()
            category = response.json()
            
            print(f"カテゴリー '{category_name}' を作成しました (ID: {category['id']})")
            return category['id']
            
        except requests.exceptions.RequestException as e:
            print(f"カテゴリー作成エラー: {e}")
            return None
    
    def parse_html_file(self, html_file_path, append_html_file=None):
        """HTMLファイルを解析してタイトルと本文を抽出"""
        try:
            with open(html_file_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # タイトルを取得（<title>タグまたは<h1>タグから）
            title = None
            if soup.title:
                title = soup.title.string
            elif soup.h1:
                title = soup.h1.get_text()
            
            # <body>タグの内容を取得
            body = soup.body
            if body:
                # 不要なタグを削除
                for script in body(["script", "style"]):
                    script.decompose()
                
                content = str(body)
            else:
                content = html_content
            
            # 追加HTMLファイルがある場合、bodyに追加
            if append_html_file and os.path.exists(append_html_file):
                try:
                    with open(append_html_file, 'r', encoding='utf-8') as append_file:
                        append_content = append_file.read()
                    
                    append_soup = BeautifulSoup(append_content, 'html.parser')
                    
                    # 追加ファイルのbodyタグの内容を取得
                    append_body = append_soup.body
                    if append_body:
                        # 不要なタグを削除
                        for script in append_body(["script", "style"]):
                            script.decompose()
                        
                        append_body_content = append_body.decode_contents()
                    else:
                        # bodyタグがない場合は全体を使用
                        append_body_content = append_content
                    
                    # 元のbodyの終了タグの前に追加
                    if content.endswith('</body>'):
                        content = content[:-7] + append_body_content + '</body>'
                    else:
                        content += append_body_content
                    
                    print(f"✅ 追加HTMLファイルを結合しました: {append_html_file}")
                    
                except Exception as e:
                    print(f"⚠️ 追加HTMLファイルの読み込みに失敗: {e}")
            
            return title, content
            
        except Exception as e:
            print(f"HTMLファイル解析エラー: {e}")
            return None, None
    
    def post_article(self, html_file_path, append_html_file=None):
        """記事を投稿（固定設定: draft状態、カテゴリーID 17）"""
        # HTMLファイルを解析
        title, content = self.parse_html_file(html_file_path, append_html_file)
        if not title or not content:
            print("HTMLファイルの解析に失敗しました")
            return None

        # 固定設定
        category_id = 17  # 施術動画カテゴリー
        status = "draft"  # 下書き状態
        category_name = "施術動画"
        
        # YouTubeリンクを検索（優先順位: ファイル名 > HTML内容）
        youtube_url, thumbnail_url, video_id = self.extract_youtube_id_from_filename(html_file_path)
        
        # ファイル名から取得できない場合、HTML内容から検索
        if not video_id:
            youtube_url, thumbnail_url, video_id = self.extract_youtube_link_from_html(content)
        
        featured_media_id = None
        
        if youtube_url:
            print(f"🎥 YouTube動画を検出: {youtube_url}")
            
            # YouTubeサムネイルをアップロードしてアイキャッチ画像に設定
            featured_media_id = self.upload_youtube_thumbnail(thumbnail_url, title, video_id)
            
            # CSSスタイルとJavaScriptを追加（WordPressテーマ対応）
            youtube_click_enhancement = f'''
<style>
.p-single__thumb {{
    position: relative !important;
    cursor: pointer !important;
}}

.p-single__thumb::before {{
    content: "▶";
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: white;
    font-size: 60px;
    text-shadow: 0 0 20px rgba(0,0,0,0.8);
    z-index: 10;
    pointer-events: none;
    transition: all 0.3s ease;
}}

.p-single__thumb:hover::before {{
    transform: translate(-50%, -50%) scale(1.2);
    text-shadow: 0 0 30px rgba(0,0,0,0.9);
}}

.p-single__thumb:hover img {{
    opacity: 0.8;
    transform: scale(1.02);
}}

.p-single__thumb img {{
    transition: all 0.3s ease;
}}

/* スタイリッシュなYouTubeボタン */
.youtube-link-button {{
    display: inline-flex;
    align-items: center;
    gap: 12px;
    background: linear-gradient(135deg, #FF0000, #FF4444);
    color: white;
    text-decoration: none;
    padding: 16px 24px;
    border-radius: 12px;
    font-weight: bold;
    font-size: 16px;
    box-shadow: 0 4px 15px rgba(255, 0, 0, 0.3);
    transition: all 0.3s ease;
    margin: 20px 0;
    max-width: 300px;
}}

.youtube-link-button:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(255, 0, 0, 0.4);
    background: linear-gradient(135deg, #FF2222, #FF6666);
    color: white;
    text-decoration: none;
}}

.youtube-link-button::before {{
    content: "▶";
    background: rgba(255, 255, 255, 0.2);
    border-radius: 50%;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
}}

.youtube-link-button:active {{
    transform: translateY(0);
    box-shadow: 0 2px 10px rgba(255, 0, 0, 0.3);
}}
</style>

<script>
document.addEventListener('DOMContentLoaded', function() {{
    const thumbnail = document.querySelector('.p-single__thumb');
    if (thumbnail) {{
        thumbnail.addEventListener('click', function() {{
            window.open('{youtube_url}', '_blank');
        }});
    }}
}});
</script>
'''
            
            # スタイリッシュなYouTubeリンクボタンを追加
            youtube_link_button = f'''
<div style="text-align: center; margin: 30px 0;">
    <a href="{youtube_url}" target="_blank" class="youtube-link-button">
        YouTubeで詳しい解説を見る
    </a>
</div>
'''
            
            # 記事の最後にスタイルとボタンを追加
            if content.endswith('</body>'):
                content = content[:-7] + youtube_click_enhancement + youtube_link_button + '</body>'
            else:
                content += youtube_click_enhancement + youtube_link_button
        
        # 投稿データを準備
        post_data = {
            'title': title,
            'content': content,
            'status': status,
            'categories': [category_id],
            'format': 'standard'
        }
        
        # アイキャッチ画像が設定できた場合は追加
        if featured_media_id:
            post_data['featured_media'] = featured_media_id
        
        try:
            print("=== 投稿データ ===")
            print(f"タイトル: {title}")
            print(f"ステータス: {status}")
            print(f"カテゴリー: {category_name} (ID: {category_id})")
            print(f"本文の長さ: {len(content)} 文字")
            if featured_media_id:
                print(f"アイキャッチ画像: メディアID {featured_media_id}")
            print("\n投稿を実行しています...")
            
            response = requests.post(
                f"{self.api_url}/posts",
                headers=self.headers,
                data=json.dumps(post_data)
            )
            response.raise_for_status()
            result = response.json()
            
            print("=== 投稿成功 ===")
            print(f"投稿ID: {result['id']}")
            print(f"投稿URL: {result['link']}")
            print(f"編集URL: {self.site_url}/wp-admin/post.php?post={result['id']}&action=edit")
            if featured_media_id:
                print(f"🖼️ アイキャッチ画像: YouTubeサムネイル (メディアID: {featured_media_id})")
                print("   → <figure class=\"p-single__thumb\"> にYouTubeサムネイルが表示されます")
            
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"投稿エラー: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"レスポンス: {e.response.text}")
            return None
    
    def extract_youtube_id_from_filename(self, html_file_path):
        """ファイル名からYouTube IDを抽出"""
        import re
        import os
        
        filename = os.path.basename(html_file_path)
        
        # ファイル名パターン: article_[YOUTUBE_ID]_[DATE]_[TIME].html
        # 例: article_pyPfHTfVcqU_20250719_153851.html
        pattern = r'article_([a-zA-Z0-9_-]{11})_\d{8}_\d{6}\.html'
        match = re.match(pattern, filename)
        
        if match:
            video_id = match.group(1)
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            print(f"🎥 ファイル名からYouTube IDを検出: {video_id}")
            return youtube_url, thumbnail_url, video_id
        
        return None, None, None
    
    def extract_youtube_link_from_html(self, content):
        """HTMLからYouTubeリンクを抽出"""
        import re
        
        # YouTubeリンクのパターンを検索
        youtube_patterns = [
            r'https://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'https://youtu\.be/([a-zA-Z0-9_-]+)',
            r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'youtu\.be/([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in youtube_patterns:
            match = re.search(pattern, content)
            if match:
                video_id = match.group(1)
                youtube_url = f"https://www.youtube.com/watch?v={video_id}"
                thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                print(f"🎥 HTML内容からYouTube IDを検出: {video_id}")
                return youtube_url, thumbnail_url, video_id
        
        return None, None, None
    
    def upload_youtube_thumbnail(self, thumbnail_url, video_title, video_id):
        """YouTubeサムネイルをWordPressメディアライブラリにアップロード"""
        try:
            print(f"📥 YouTubeサムネイルをダウンロード中: {thumbnail_url}")
            
            # サムネイル画像をダウンロード
            response = requests.get(thumbnail_url, timeout=30)
            response.raise_for_status()
            
            # ファイル名を生成（日本語対応）
            safe_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"youtube_{video_id}_{safe_title[:50]}.jpg"
            
            # WordPressメディアAPIにアップロード
            files = {
                'file': (filename, response.content, 'image/jpeg')
            }
            
            # メタデータも送信
            data = {
                'title': f"YouTube動画サムネイル: {video_title}",
                'alt_text': video_title,
                'caption': f"YouTube動画: {video_title}",
                'description': f"YouTube動画のサムネイル画像 (Video ID: {video_id})"
            }
            
            print(f"📤 WordPressメディアライブラリにアップロード中...")
            upload_response = requests.post(
                f"{self.api_url}/media",
                headers={'Authorization': self.headers['Authorization']},
                files=files,
                data=data
            )
            upload_response.raise_for_status()
            media_data = upload_response.json()
            
            print(f"✅ YouTubeサムネイルをアップロードしました")
            print(f"   メディアID: {media_data['id']}")
            print(f"   URL: {media_data['source_url']}")
            return media_data['id']
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️ サムネイルアップロードに失敗: {e}")
            # 高解像度サムネイルが失敗した場合、標準解像度を試す
            try:
                standard_thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                print(f"📥 標準解像度サムネイルで再試行: {standard_thumbnail_url}")
                
                response = requests.get(standard_thumbnail_url, timeout=30)
                response.raise_for_status()
                
                files = {
                    'file': (f"youtube_{video_id}_standard.jpg", response.content, 'image/jpeg')
                }
                
                upload_response = requests.post(
                    f"{self.api_url}/media",
                    headers={'Authorization': self.headers['Authorization']},
                    files=files
                )
                upload_response.raise_for_status()
                media_data = upload_response.json()
                
                print(f"✅ 標準解像度サムネイルをアップロードしました (メディアID: {media_data['id']})")
                return media_data['id']
                
            except Exception as fallback_error:
                print(f"❌ 標準解像度サムネイルでも失敗: {fallback_error}")
                return None
    
    def test_connection(self):
        """API接続をテスト"""
        try:
            response = requests.get(f"{self.api_url}/posts?per_page=1", headers=self.headers)
            response.raise_for_status()
            print("✅ WordPress API接続成功")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ WordPress API接続失敗: {e}")
            return False
        """API接続をテスト"""
        try:
            response = requests.get(f"{self.api_url}/posts?per_page=1", headers=self.headers)
            response.raise_for_status()
            print("✅ WordPress API接続成功")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ WordPress API接続失敗: {e}")
            return False

def main():
    # 設定（実際の値に変更してください）
    SITE_URL = "https://almoprs-clinic.jp"  # あなたのWordPressサイトURL
    USERNAME = "Uchida"  # WordPressユーザー名
    APP_PASSWORD = "uKnn KRGv weGO FBCv y84y mbON"  # Application Password
    
    # === 固定設定 ===
    # ステータス: draft（下書き）
    # カテゴリー: 施術動画 (ID: 17)
    
    # 常に追加するHTMLファイル（フッター用）
    APPEND_HTML_FILE = "footer.html"  # 追加したいHTMLファイルのパス
    # または None に設定すると追加しない
    # APPEND_HTML_FILE = None
    
    # HTMLファイルのパス指定方法
    # コマンドライン引数で指定（必須）
    if len(sys.argv) < 2:
        print("❌ HTMLファイルのパスを指定してください")
        print("使用方法:")
        print("  python wordpress_test.py <HTMLファイル> [追加HTMLファイル]")
        print("例:")
        print("  python wordpress_test.py article.html")
        print("  python wordpress_test.py article.html footer.html")
        return
    
    HTML_FILE_PATH = sys.argv[1]
    print(f"使用するHTMLファイル: {HTML_FILE_PATH}")
    
    # 2つ目の引数で追加HTMLファイルを指定
    if len(sys.argv) > 2:
        APPEND_HTML_FILE = sys.argv[2]
        print(f"追加HTMLファイル: {APPEND_HTML_FILE}")
    
    # WordPressAPIテスターを初期化
    wp_tester = WordPressAPITester(SITE_URL, USERNAME, APP_PASSWORD)
    
    # 接続テスト
    if not wp_tester.test_connection():
        print("WordPress APIに接続できません。設定を確認してください。")
        return
    
    # HTMLファイルが存在するかチェック
    if not os.path.exists(HTML_FILE_PATH):
        print(f"❌ HTMLファイルが見つかりません: {HTML_FILE_PATH}")
        print(f"現在のディレクトリ: {os.getcwd()}")
        print("\n利用可能なHTMLファイル:")
        html_files = [f for f in os.listdir('.') if f.endswith('.html')]
        if html_files:
            for f in html_files:
                print(f"  - {f}")
        else:
            print("  HTMLファイルが見つかりません")
        return
    
    # 追加HTMLファイルの存在チェック
    if APPEND_HTML_FILE and not os.path.exists(APPEND_HTML_FILE):
        print(f"⚠️ 追加HTMLファイルが見つかりません: {APPEND_HTML_FILE}")
        print("追加HTMLファイルなしで続行します...")
        APPEND_HTML_FILE = None
    
    # 記事を下書きとして投稿（固定設定）
    result = wp_tester.post_article(
        html_file_path=HTML_FILE_PATH,
        append_html_file=APPEND_HTML_FILE
    )
    
    if result:
        print("\n=== 投稿完了 ===")
        print("WordPress管理画面で下書きを確認してください。")
    else:
        print("投稿に失敗しました。")

if __name__ == "__main__":
    main()