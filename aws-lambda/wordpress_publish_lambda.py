import json
import boto3
import os
import re
import requests
import base64
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import unquote

# AWS clients
s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    Lambda関数3: HTML記事をWordPressに自動投稿
    
    Input: S3のHTML記事ファイル
    Output: WordPressに下書き投稿
    """
    
    try:
        print("🚀 WordPress投稿開始")
        
        # S3イベントまたは直接呼び出しからHTML記事ファイル情報を取得
        if 'Records' in event:
            # S3イベントからの呼び出し
            bucket = event['Records'][0]['s3']['bucket']['name']
            article_key = unquote(event['Records'][0]['s3']['object']['key'])
        else:
            # 直接呼び出し（API Gateway等）
            bucket = event.get('bucket')
            article_key = event.get('article_key')
            
        if not bucket or not article_key:
            raise ValueError("bucket and article_key are required")
        
        print(f"📁 S3バケット: {bucket}")
        print(f"📄 HTML記事ファイル: {article_key}")
        
        # S3からHTML記事ファイルを取得
        response = s3.get_object(Bucket=bucket, Key=article_key)
        html_content = response['Body'].read().decode('utf-8')
        
        # WordPress設定（環境変数から取得）
        wp_config = {
            'site_url': os.environ['WORDPRESS_SITE_URL'],
            'username': os.environ['WORDPRESS_USERNAME'],
            'app_password': os.environ['WORDPRESS_APP_PASSWORD']
        }
        
        # WordPress APIクライアントを初期化
        wp_client = WordPressAPIClient(**wp_config)
        
        # HTML記事をWordPressに投稿（フッターファイルを含む）
        result = wp_client.post_article_from_html(html_content, article_key)
        
        if not result:
            raise Exception("WordPress投稿に失敗しました")
        
        # 投稿結果をメタデータとして保存
        video_id = extract_video_id_from_filename(article_key)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        metadata = {
            "wordpress_info": {
                "post_id": result['id'],
                "post_url": result['link'],
                "edit_url": f"{wp_config['site_url']}/wp-admin/post.php?post={result['id']}&action=edit",
                "status": "draft",
                "published_at": datetime.now().isoformat()
            },
            "processing_info": {
                "processed_at": datetime.now().isoformat(),
                "status": "wordpress_completed",
                "lambda_function": "wordpress_publish",
                "article_key": article_key
            }
        }
        
        metadata_key = f"metadata/wordpress_{video_id}_{timestamp}.json"
        s3.put_object(
            Bucket=bucket,
            Key=metadata_key,
            Body=json.dumps(metadata, ensure_ascii=False, indent=2).encode('utf-8'),
            ContentType='application/json'
        )
        
        print("✅ WordPress投稿完了！")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'WordPress投稿完了',
                'post_id': result['id'],
                'post_url': result['link'],
                'edit_url': metadata['wordpress_info']['edit_url'],
                'metadata_key': metadata_key
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            }, ensure_ascii=False)
        }

def extract_video_id_from_filename(filename):
    """ファイル名からYouTube IDを抽出"""
    import os
    
    filename = os.path.basename(filename)
    
    # ファイル名パターン: article_[YOUTUBE_ID]_[DATE]_[TIME].html
    pattern = r'article_([a-zA-Z0-9_-]{11})_\d{8}_\d{6}\.html'
    match = re.match(pattern, filename)
    
    if match:
        return match.group(1)
    
    return 'unknown'

class WordPressAPIClient:
    """WordPress API クライアント"""
    
    def __init__(self, site_url, username, app_password):
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
    
    def post_article_from_html(self, html_content, filename):
        """HTML内容からWordPress記事を投稿"""
        
        # HTMLを解析してタイトルと本文を抽出
        title, content = self.parse_html_content(html_content)
        if not title or not content:
            raise Exception("HTML解析に失敗しました")
        
        # S3からフッターファイルを読み込んで追加
        content = self.append_footer_from_s3(content)
        
        # 固定設定
        category_id = 17  # 施術動画カテゴリー
        status = "draft"  # 下書き状態
        
        # YouTubeリンクを検索
        youtube_url, thumbnail_url, video_id = self.extract_youtube_info(filename, content)
        
        featured_media_id = None
        
        if youtube_url:
            print(f"🎥 YouTube動画を検出: {youtube_url}")
            
            # YouTubeサムネイルをアップロードしてアイキャッチ画像に設定
            featured_media_id = self.upload_youtube_thumbnail(thumbnail_url, title, video_id)
            
            # YouTube連携の拡張機能を追加
            content = self.enhance_content_with_youtube(content, youtube_url)
        
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
            print(f"📝 投稿データ:")
            print(f"   タイトル: {title}")
            print(f"   ステータス: {status}")
            print(f"   カテゴリー: 施術動画 (ID: {category_id})")
            print(f"   本文の長さ: {len(content)} 文字")
            if featured_media_id:
                print(f"   アイキャッチ画像: メディアID {featured_media_id}")
            
            response = requests.post(
                f"{self.api_url}/posts",
                headers=self.headers,
                data=json.dumps(post_data),
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            
            print("=== 投稿成功 ===")
            print(f"投稿ID: {result['id']}")
            print(f"投稿URL: {result['link']}")
            print(f"編集URL: {self.site_url}/wp-admin/post.php?post={result['id']}&action=edit")
            
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 投稿エラー: {e}")
            raise e
    
    def parse_html_content(self, html_content):
        """HTMLコンテンツを解析してタイトルと本文を抽出"""
        try:
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
            
            return title, content
            
        except Exception as e:
            print(f"HTML解析エラー: {e}")
            return None, None
    
    def extract_youtube_info(self, filename, content):
        """ファイル名またはHTMLからYouTube情報を抽出"""
        
        # ファイル名から抽出を試行
        video_id = extract_video_id_from_filename(filename)
        if video_id and video_id != 'unknown':
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            return youtube_url, thumbnail_url, video_id
        
        # HTML内容から検索
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
                return youtube_url, thumbnail_url, video_id
        
        return None, None, None
    
    def upload_youtube_thumbnail(self, thumbnail_url, video_title, video_id):
        """YouTubeサムネイルをWordPressメディアライブラリにアップロード"""
        try:
            print(f"📥 YouTubeサムネイルをダウンロード中: {thumbnail_url}")
            
            # サムネイル画像をダウンロード
            response = requests.get(thumbnail_url, timeout=30)
            response.raise_for_status()
            
            # ファイル名を生成
            safe_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"youtube_{video_id}_{safe_title[:50]}.jpg"
            
            # WordPressメディアAPIにアップロード
            files = {
                'file': (filename, response.content, 'image/jpeg')
            }
            
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
                data=data,
                timeout=60
            )
            upload_response.raise_for_status()
            media_data = upload_response.json()
            
            print(f"✅ YouTubeサムネイルをアップロードしました (メディアID: {media_data['id']})")
            return media_data['id']
            
        except Exception as e:
            print(f"⚠️ サムネイルアップロードに失敗: {e}")
            return None
    
    def enhance_content_with_youtube(self, content, youtube_url):
        """コンテンツにYouTube連携機能を追加"""
        
        # CSSスタイルとJavaScriptを追加
        youtube_enhancement = f'''
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
        
        # YouTubeリンクボタンを追加
        youtube_link_button = f'''
<div style="text-align: center; margin: 30px 0;">
    <a href="{youtube_url}" target="_blank" class="youtube-link-button">
        YouTubeで詳しい解説を見る
    </a>
</div>
'''
        
        # 記事の最後にスタイルとボタンを追加
        if content.endswith('</body>'):
            content = content[:-7] + youtube_enhancement + youtube_link_button + '</body>'
        else:
            content += youtube_enhancement + youtube_link_button
        
        return content
    
    def append_footer_from_s3(self, content):
        """S3からフッターHTMLファイルを読み込んで本文に追加"""
        try:
            # S3バケット名を環境変数から取得
            bucket = os.environ.get('S3_BUCKET', 'video-article-processing-prod')
            footer_key = 'templates/footer.html'
            
            print(f"📥 S3からフッターファイルを読み込み中: s3://{bucket}/{footer_key}")
            
            # S3からフッターファイルを取得
            response = s3.get_object(Bucket=bucket, Key=footer_key)
            footer_content = response['Body'].read().decode('utf-8')
            
            footer_soup = BeautifulSoup(footer_content, 'html.parser')
            
            # フッターファイルのbodyタグの内容を取得
            footer_body = footer_soup.body
            if footer_body:
                # 不要なタグを削除
                for script in footer_body(["script", "style"]):
                    script.decompose()
                
                footer_body_content = footer_body.decode_contents()
            else:
                # bodyタグがない場合は全体を使用
                footer_body_content = footer_content
            
            # 元のbodyの終了タグの前に追加
            if content.endswith('</body>'):
                content = content[:-7] + footer_body_content + '</body>'
            else:
                content += footer_body_content
            
            print("✅ S3からフッターHTMLファイルを結合しました")
            
        except Exception as e:
            print(f"⚠️ S3フッターHTMLファイルの読み込みに失敗: {e}")
            print("フッターなしで続行します...")
        
        return content