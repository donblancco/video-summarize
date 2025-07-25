import json
import boto3
import os
import re
from datetime import datetime
import openai
from urllib.parse import unquote

# AWS clients
s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    Lambda関数2: 文字起こしファイルからHTML記事生成
    
    Input: S3の文字起こしファイル
    Output: S3にHTML記事ファイル保存
    """
    
    try:
        print("🚀 HTML記事生成開始")
        
        # S3イベントまたは直接呼び出しから文字起こしファイル情報を取得
        if 'Records' in event:
            # S3イベントからの呼び出し
            bucket = event['Records'][0]['s3']['bucket']['name']
            transcript_key = unquote(event['Records'][0]['s3']['object']['key'])
        else:
            # 直接呼び出し（API Gateway等）
            bucket = event.get('bucket')
            transcript_key = event.get('transcript_key')
            
        if not bucket or not transcript_key:
            raise ValueError("bucket and transcript_key are required")
        
        print(f"📁 S3バケット: {bucket}")
        print(f"📝 文字起こしファイル: {transcript_key}")
        
        # S3から文字起こしファイルを取得
        response = s3.get_object(Bucket=bucket, Key=transcript_key)
        transcript_content = response['Body'].read().decode('utf-8')
        
        # 文字起こしファイルを解析
        video_info, transcript_text, full_content = parse_transcript_content(transcript_content)
        
        if not video_info or not transcript_text:
            raise Exception("文字起こしファイルの解析に失敗しました")
        
        print(f"📋 動画情報:")
        print(f"   タイトル: {video_info['title']}")
        print(f"   投稿者: {video_info['uploader']}")
        print(f"   動画ID: {video_info['id']}")
        print(f"   文字起こし長: {len(transcript_text):,}文字")
        
        # HTML記事生成
        html_content = generate_article(video_info, transcript_text)
        
        if not html_content:
            raise Exception("記事生成に失敗しました")
        
        # タイムスタンプ生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # S3にHTML記事ファイルをアップロード
        article_key = f"articles/article_{video_info['id']}_{timestamp}.html"
        print(f"📤 S3にHTML記事アップロード中: {article_key}")
        s3.put_object(
            Bucket=bucket,
            Key=article_key,
            Body=html_content.encode('utf-8'),
            ContentType='text/html'
        )
        
        # メタデータファイルを更新
        metadata = {
            "video_info": {
                "video_id": video_info['id'],
                "title": video_info['title'],
                "uploader": video_info['uploader'],
                "duration": video_info['duration'],
                "upload_date": video_info['upload_date'],
                "url": video_info['url'],
                "thumbnail": f"https://i.ytimg.com/vi/{video_info['id']}/maxresdefault.jpg"
            },
            "processing_info": {
                "processed_at": datetime.now().isoformat(),
                "status": "article_completed",
                "lambda_function": "generate_article",
                "transcript_key": transcript_key,
                "article_key": article_key,
                "file_sizes": {
                    "transcript_length": len(full_content),
                    "article_length": len(html_content)
                }
            },
            "system_info": {
                "python_version": "3.11",
                "openai_model_gpt": "gpt-4-turbo"
            }
        }
        
        metadata_key = f"metadata/article_{video_info['id']}_{timestamp}.json"
        s3.put_object(
            Bucket=bucket,
            Key=metadata_key,
            Body=json.dumps(metadata, ensure_ascii=False, indent=2).encode('utf-8'),
            ContentType='application/json'
        )
        
        print("✅ HTML記事生成完了！")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'HTML記事生成完了',
                'video_id': video_info['id'],
                'article_key': article_key,
                'metadata_key': metadata_key,
                'article_length': len(html_content)
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

def parse_transcript_content(content):
    """文字起こしファイルの内容を解析して情報を抽出"""
    try:
        lines = content.split('\n')
        video_info = {}
        
        # ヘッダー情報を解析
        for line in lines[:10]:  # 最初の10行から情報を抽出
            if line.startswith('動画タイトル:'):
                video_info['title'] = line.replace('動画タイトル:', '').strip()
            elif line.startswith('URL:'):
                video_info['url'] = line.replace('URL:', '').strip()
            elif line.startswith('投稿者:'):
                video_info['uploader'] = line.replace('投稿者:', '').strip()
            elif line.startswith('投稿日:'):
                video_info['upload_date'] = line.replace('投稿日:', '').strip()
            elif line.startswith('動画時間:'):
                duration_str = line.replace('動画時間:', '').replace('秒', '').strip()
                video_info['duration'] = int(duration_str) if duration_str.isdigit() else 0
        
        # 動画IDをURLから抽出
        url = video_info.get('url', '')
        video_id_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)', url)
        video_info['id'] = video_id_match.group(1) if video_id_match else 'unknown'
        
        # 文字起こし内容を抽出
        start_index = -1
        for i, line in enumerate(lines):
            if '文字起こし内容' in line:
                start_index = i + 3  # ヘッダーの後の空行をスキップ
                break
        
        if start_index > 0:
            transcript_text = '\n'.join(lines[start_index:])
        else:
            transcript_text = content
        
        return video_info, transcript_text, content
        
    except Exception as e:
        print(f"❌ 文字起こしファイル解析エラー: {str(e)}")
        return None, None, None

def generate_article(video_info, transcript_text):
    """文字起こしから記事を生成"""
    print("📄 記事生成中...")
    
    # OpenAI 0.28.0 安定版での初期化
    try:
        openai.api_key = os.environ['OPENAI_API_KEY']
        print(f"✅ OpenAI初期化成功 (バージョン: {openai.__version__})")
    except Exception as e:
        print(f"❌ OpenAI初期化エラー: {str(e)}")
        raise
    
    prompt = f"""
以下のYouTube動画の文字起こしから、SEO最適化されたブログ記事を作成してください。

動画タイトル: {video_info['title']}
動画URL: {video_info['url']}
投稿者: {video_info['uploader']}

文字起こし:
{transcript_text}

記事の要件:
1. タイトルは内容を的確に表現し、検索されやすいものにする
2. 見出しタグ（h2, h3）を適切に使用して構造化する
3. 重要なポイントを箇条書きや表でまとめる
4. 専門用語には簡潔な説明を加える
5. 読者が行動を起こしやすいような結論を含める
6. 最後に動画リンクを含める（「詳しい解説は動画でご確認ください」等）
7. HTML形式で出力する（<!DOCTYPE html>から</html>まで完全な形で）
8. 不要な要素（CSS、JavaScript、メタ情報等）は含めない
"""
    
    try:
        # OpenAI 0.28.0 旧API形式（安定版）
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "あなたは医療・健康分野に精通したプロのブログライターです。正確で分かりやすい記事を作成します。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.7
        )
        
        article = response.choices[0].message.content
        
        # Markdownのコードブロック記号を除去
        if article.startswith('```html'):
            article = article[7:]  # '```html' を除去
        elif article.startswith('```'):
            article = article[3:]   # '```' を除去
        
        if article.endswith('```'):
            article = article[:-3]  # 末尾の '```' を除去
        
        article = article.strip()  # 前後の空白を除去
        
        print(f"✅ 記事生成完了 ({len(article)}文字)")
        return article
        
    except Exception as e:
        print(f"❌ 記事生成エラー: {str(e)}")
        return None