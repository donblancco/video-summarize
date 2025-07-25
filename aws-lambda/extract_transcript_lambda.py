import json
import boto3
import os
import re
import tempfile
from datetime import datetime
import openai
from urllib.parse import unquote
# pydubはContainer環境では不要（FFmpegを直接使用）

# AWS clients
s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    Lambda関数1: 動画から音声抽出・文字起こし
    
    Input: 
    - S3に動画ファイルがアップロードされる
    - イベントにYouTube URLが含まれる
    
    Output:
    - S3に音声ファイル保存
    - S3に文字起こしファイル保存
    """
    
    try:
        print("🚀 音声抽出・文字起こし処理開始")
        
        # S3イベントまたはAPI Gatewayイベントから情報を取得
        if 'Records' in event:
            # S3イベントからの呼び出し
            bucket = event['Records'][0]['s3']['bucket']['name']
            video_key = unquote(event['Records'][0]['s3']['object']['key'])
            
            # メタデータからYouTube URLを取得
            response = s3.head_object(Bucket=bucket, Key=video_key)
            youtube_url = response.get('Metadata', {}).get('youtube-url', '')
            
        else:
            # API Gatewayからの呼び出し
            body = json.loads(event.get('body', '{}'))
            bucket = body.get('bucket')
            video_key = body.get('video_key')
            youtube_url = body.get('youtube_url', '')
        
        if not bucket or not video_key:
            raise ValueError("bucket and video_key are required")
        
        print(f"📁 S3バケット: {bucket}")
        print(f"🎬 動画ファイル: {video_key}")
        print(f"🔗 YouTube URL: {youtube_url}")
        
        # YouTube URLから動画IDを抽出
        video_id = extract_video_id(youtube_url)
        if not video_id:
            video_id = 'unknown'
        
        print(f"🆔 動画ID: {video_id}")
        
        # タイムスタンプ生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 一時ディレクトリで処理
        with tempfile.TemporaryDirectory() as temp_dir:
            # S3から動画ファイルをダウンロード
            video_path = os.path.join(temp_dir, 'input_video.mp4')
            print(f"📥 S3から動画ダウンロード中: {video_key}")
            s3.download_file(bucket, video_key, video_path)
            
            # 音声抽出
            audio_data = extract_audio_from_file(video_path, temp_dir, video_id)
            if not audio_data:
                raise Exception("音声抽出に失敗しました")
            
            # S3に音声ファイルをアップロード
            audio_key = f"audio/{video_id}.mp3"
            print(f"📤 S3に音声アップロード中: {audio_key}")
            s3.upload_file(audio_data['file_path'], bucket, audio_key)
            
            # 動画情報を設定
            video_info = {
                'id': video_id,
                'title': f"動画 ({os.path.basename(video_key)})",
                'uploader': '不明',
                'duration': audio_data['duration'],
                'upload_date': datetime.now().strftime('%Y%m%d'),
                'url': youtube_url
            }
            
            # 文字起こし
            transcript_content = transcribe_audio(audio_data['file_path'], video_info)
            if not transcript_content:
                raise Exception("文字起こしに失敗しました")
            
            # S3に文字起こしファイルをアップロード
            transcript_key = f"transcripts/transcript_{video_id}_{timestamp}.txt"
            print(f"📤 S3に文字起こしアップロード中: {transcript_key}")
            s3.put_object(
                Bucket=bucket,
                Key=transcript_key,
                Body=transcript_content.encode('utf-8'),
                ContentType='text/plain'
            )
            
            # メタデータファイルを作成
            metadata = {
                "video_info": video_info,
                "processing_info": {
                    "processed_at": datetime.now().isoformat(),
                    "status": "transcript_completed",
                    "lambda_function": "extract_transcript",
                    "audio_key": audio_key,
                    "transcript_key": transcript_key,
                    "file_sizes": {
                        "audio_mb": audio_data['file_size_mb'],
                        "transcript_length": len(transcript_content)
                    }
                }
            }
            
            metadata_key = f"metadata/extract_{video_id}_{timestamp}.json"
            s3.put_object(
                Bucket=bucket,
                Key=metadata_key,
                Body=json.dumps(metadata, ensure_ascii=False, indent=2).encode('utf-8'),
                ContentType='application/json'
            )
            
            print("✅ 音声抽出・文字起こし完了！")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': '音声抽出・文字起こし完了',
                    'video_id': video_id,
                    'audio_key': audio_key,
                    'transcript_key': transcript_key,
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

def extract_video_id(youtube_url):
    """YouTube URLから動画IDを抽出"""
    if not youtube_url:
        return None
    
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]+)',
        r'youtube\.com/watch\?.*v=([\w-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
    return None

def extract_audio_from_file(video_path, output_dir, video_id):
    """動画ファイルから音声を抽出（FFmpeg Container対応）"""
    print(f"🎵 音声処理中: {video_path}")
    
    # ファイル拡張子を確認
    file_ext = os.path.splitext(video_path)[1].lower()
    output_file = os.path.join(output_dir, f"{video_id}.mp3")
    
    if file_ext in ['.mp3', '.wav', '.m4a', '.aac']:
        # 既に音声ファイルの場合はコピー
        print(f"🔄 音声ファイルをコピー中...")
        import shutil
        shutil.copy2(video_path, output_file)
        
        # ファイル名をMP3に統一
        if file_ext != '.mp3':
            temp_output = os.path.join(output_dir, f"{video_id}_temp{file_ext}")
            shutil.move(output_file, temp_output)
            
            # FFmpegで形式変換
            try:
                import subprocess
                cmd = [
                    '/usr/local/bin/ffmpeg', '-i', temp_output,
                    '-acodec', 'mp3', '-ab', '128k', '-ar', '44100',
                    '-y', output_file
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode != 0:
                    print(f"⚠️ 形式変換に失敗、元ファイルを使用: {result.stderr}")
                    shutil.move(temp_output, output_file)
                else:
                    os.remove(temp_output)
                    print(f"✅ {file_ext} から MP3 に変換完了")
                    
            except Exception as e:
                print(f"⚠️ 形式変換エラー、元ファイルを使用: {e}")
                shutil.move(temp_output, output_file)
    
    elif file_ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']:
        # 動画ファイルの場合はFFmpegで音声抽出
        print(f"🔧 FFmpegで動画から音声抽出中: {file_ext}")
        
        try:
            import subprocess
            cmd = [
                '/usr/local/bin/ffmpeg', '-i', video_path,
                '-vn',  # 映像なし
                '-acodec', 'mp3',  # MP3エンコード
                '-ab', '128k',  # ビットレート
                '-ar', '44100',  # サンプリングレート
                '-y',  # 上書き
                output_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                print(f"❌ FFmpeg音声抽出エラー: {result.stderr}")
                return None
                
            print(f"✅ FFmpegで音声抽出完了")
            
        except subprocess.TimeoutExpired:
            print("❌ FFmpeg実行がタイムアウトしました")
            return None
        except Exception as e:
            print(f"❌ 音声抽出エラー: {str(e)}")
            return None
    
    else:
        print(f"❌ 未対応のファイル形式: {file_ext}")
        print("💡 対応形式: 動画(.mp4,.avi,.mov,.mkv,.webm,.flv,.wmv) 音声(.mp3,.wav,.m4a,.aac)")
        return None
    
    # ファイル情報を取得
    if not os.path.exists(output_file):
        print("❌ 音声ファイルが作成されませんでした")
        return None
        
    file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
    
    # 音声の長さを取得（FFprobeで）
    try:
        import subprocess
        cmd = [
            '/usr/local/bin/ffprobe', '-v', 'quiet', '-show_entries',
            'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
            output_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0 and result.stdout.strip():
            duration = int(float(result.stdout.strip()))
        else:
            # フォールバック: ファイルサイズから推定
            duration = int(file_size_mb * 8)  # 1MB ≈ 8秒
            print(f"⚠️ FFprobe失敗、推定時間を使用: {duration}秒")
            
    except Exception as e:
        duration = int(file_size_mb * 8)
        print(f"⚠️ 音声長取得失敗、推定時間を使用: {e}")
    
    print(f"✅ 音声処理完了: {output_file}")
    print(f"    📊 ファイルサイズ: {file_size_mb:.1f} MB")
    print(f"    ⏱️ 時間: {duration}秒")
    
    return {
        'file_path': output_file,
        'video_id': video_id,
        'duration': duration,
        'file_size_mb': file_size_mb
    }

def transcribe_audio(audio_file_path, video_info):
    """音声を文字起こし"""
    print(f"📝 文字起こし中: {audio_file_path}")
    
    # OpenAI 0.28.0 安定版での初期化
    try:
        openai.api_key = os.environ['OPENAI_API_KEY']
        print(f"✅ OpenAI初期化成功 (バージョン: {openai.__version__})")
    except Exception as e:
        print(f"❌ OpenAI初期化エラー: {str(e)}")
        raise
    
    try:
        with open(audio_file_path, 'rb') as audio_file:
            # OpenAI 0.28.0 旧API形式（安定版）
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                language="ja"
            )
            
        transcript_text = transcript.get('text', '')
        print(f"✅ 文字起こし完了 ({len(transcript_text)}文字)")
        
        # フォーマットされた文字起こしファイルを生成
        transcript_content = f"""動画タイトル: {video_info['title']}
URL: {video_info['url']}
投稿者: {video_info['uploader']}
投稿日: {video_info['upload_date']}
動画時間: {video_info['duration']}秒
処理日時: {datetime.now().isoformat()}

==================================================
文字起こし内容
==================================================

{transcript_text}
"""
        
        return transcript_content
        
    except Exception as e:
        print(f"❌ 文字起こしエラー: {str(e)}")
        return None