#!/usr/bin/env python3
"""
YouTube動画文字起こし＋WordPress投稿テストスクリプト
ローカル環境での動作確認用
"""

import os
import json
import yt_dlp
import openai
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

class YouTubeTranscriptionSystem:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    def get_latest_videos(self, channel_url, max_videos=5):
        """チャンネルの最新動画を取得"""
        print(f"📺 チャンネル動画を取得中: {channel_url}")
        
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'playlistend': max_videos,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(channel_url, download=False)
                videos = info.get('entries', [])
                
                print(f"✅ {len(videos)}件の動画を取得しました")
                for i, video in enumerate(videos[:3]):  # 最新3件表示
                    print(f"  {i+1}. {video.get('title', 'タイトル不明')}")
                
                return videos
                
        except Exception as e:
            print(f"❌ 動画取得エラー: {str(e)}")
            return []
    
    def get_video_details(self, video_url):
        """動画の詳細情報を取得（音声ダウンロードなし）"""
        print(f"📋 動画詳細を取得中: {video_url}")
        
        ydl_opts = {
            'quiet': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                video_details = {
                    'id': info['id'],
                    'title': info['title'],
                    'description': info.get('description', ''),
                    'thumbnail': info.get('thumbnail', ''),
                    'duration': info.get('duration', 0),
                    'upload_date': info.get('upload_date', ''),
                    'uploader': info.get('uploader', ''),
                    'view_count': info.get('view_count', 0),
                    'url': video_url
                }
                
                print(f"✅ 動画詳細取得完了: {video_details['title']}")
                return video_details
                
        except Exception as e:
            print(f"❌ 動画詳細取得エラー: {str(e)}")
            return None
    
    def download_audio(self, video_url, output_dir="./downloads"):
        """動画から音声を抽出"""
        print(f"🎵 音声をダウンロード中: {video_url}")
        
        # 出力ディレクトリ作成
        Path(output_dir).mkdir(exist_ok=True)
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{output_dir}/%(id)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url)
                audio_file = f"{output_dir}/{info['id']}.mp3"
                
                print(f"✅ 音声ダウンロード完了: {audio_file}")
                return audio_file
                
        except Exception as e:
            print(f"❌ 音声ダウンロードエラー: {str(e)}")
            return None
    
    def transcribe_audio(self, audio_file_path):
        """音声を文字起こし"""
        print(f"📝 文字起こし中: {audio_file_path}")
        
        try:
            with open(audio_file_path, 'rb') as audio_file:
                transcript = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ja"
                )
                
            print(f"✅ 文字起こし完了 ({len(transcript.text)}文字)")
            return transcript.text
            
        except Exception as e:
            print(f"❌ 文字起こしエラー: {str(e)}")
            return None
    
    def generate_article(self, video_info, transcript):
        """文字起こしから記事を生成"""
        print("📄 記事生成中...")
        
        prompt = f"""
以下のYouTube動画の文字起こしから、ブログ記事を作成してください。

動画タイトル: {video_info['title']}
動画URL: {video_info['url']}
投稿者: {video_info['uploader']}

文字起こし:
{transcript}

記事の要件:
- 読みやすい構成にする
- 重要なポイントを見出しで区切る
- 最後に動画リンクを含める
- HTML形式で出力する
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "あなたは優秀なブログライターです。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            article = response.choices[0].message.content
            print(f"✅ 記事生成完了 ({len(article)}文字)")
            return article
            
        except Exception as e:
            print(f"❌ 記事生成エラー: {str(e)}")
            return None


def main():
    """メイン処理"""
    system = YouTubeTranscriptionSystem()
    
    print("🚀 YouTube文字起こしシステム テスト開始")
    print("=" * 50)
    
    # 1. チャンネル動画取得テスト
    channel_url = "https://www.youtube.com/@naorun_shokumou/videos"
    videos = system.get_latest_videos(channel_url, max_videos=3)
    
    if not videos:
        print("❌ 動画が取得できませんでした")
        return
    
    print("\n" + "=" * 50)
    
    # 2. 最新動画を1件処理
    latest_video = videos[0]
    video_url = f"https://www.youtube.com/watch?v={latest_video['id']}"
    
    # 動画詳細取得
    video_details = system.get_video_details(video_url)
    if not video_details:
        print("❌ 動画詳細が取得できませんでした")
        return
    
    print(f"\n📊 処理対象動画:")
    print(f"  タイトル: {video_details['title']}")
    print(f"  時間: {video_details['duration']}秒")
    print(f"  投稿日: {video_details['upload_date']}")
    
    # 動画が長すぎる場合はスキップ
    if video_details['duration'] > 1800:  # 30分以上
        print("⚠️ 動画が長すぎるため、テストをスキップします")
        return
    
    print("\n" + "=" * 50)
    
    # 3. 音声ダウンロード（オプション）
    print("音声ダウンロードを実行しますか？ (y/n): ", end="")
    if input().lower() == 'y':
        audio_file = system.download_audio(video_url)
        
        if audio_file:
            print("\n" + "=" * 50)
            
            # 4. 文字起こし
            transcript = system.transcribe_audio(audio_file)
            
            if transcript:
                print(f"\n📝 文字起こし結果（最初の200文字）:")
                print(transcript[:200] + "...")
                
                print("\n" + "=" * 50)
                
                # 5. 記事生成
                article = system.generate_article(video_details, transcript)
                
                if article:
                    print(f"\n📄 生成された記事（最初の300文字）:")
                    print(article[:300] + "...")
                    
                    # 記事を保存
                    output_file = f"article_{video_details['id']}.html"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(article)
                    print(f"\n💾 記事を保存しました: {output_file}")
    
    print("\n" + "=" * 50)
    print("🎉 テスト完了！")


if __name__ == "__main__":
    main()