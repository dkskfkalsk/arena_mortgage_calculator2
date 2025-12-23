# -*- coding: utf-8 -*-
"""
Vercel 서버리스 함수 - 텔레그램 Webhook
"""

import json
import os
import sys
import asyncio

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Vercel 로그를 위해 stderr와 stdout 모두 사용
def log_debug(message):
    """디버그 로그 출력 (Vercel 로그에 표시)"""
    print(message, file=sys.stderr, flush=True)
    print(message, flush=True)

# 모듈 로드 시 로그 출력 (즉시 실행)
print("=" * 60, file=sys.stderr, flush=True)
print("DEBUG: api/webhook.py module loaded", file=sys.stderr, flush=True)
print(f"DEBUG: Python version: {sys.version}", file=sys.stderr, flush=True)
print(f"DEBUG: Working directory: {os.getcwd()}", file=sys.stderr, flush=True)
print("=" * 60, file=sys.stderr, flush=True)
# stdout에도 출력
print("=" * 60, flush=True)
print("DEBUG: api/webhook.py module loaded", flush=True)
print(f"DEBUG: Python version: {sys.version}", flush=True)
print(f"DEBUG: Working directory: {os.getcwd()}", flush=True)
print("=" * 60, flush=True)

# 전역 애플리케이션 인스턴스
application = None
_global_loop = None


def get_application():
    """텔레그램 애플리케이션 인스턴스 가져오기 (싱글톤)"""
    global application

    if application is None:
        log_debug("DEBUG: Initializing Telegram application...")
        from telegram.ext import (
            Application, MessageHandler, CommandHandler, filters
        )
        from parsers.message_parser import MessageParser
        from calculator.base_calculator import BaseCalculator
        from utils.formatter import format_all_results

        # 환경변수에서 토큰 가져오기
        TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        if not TELEGRAM_BOT_TOKEN:
            try:
                from config.telegram_config import TELEGRAM_BOT_TOKEN  # type: ignore
            except ModuleNotFoundError:
                log_debug("ERROR: TELEGRAM_BOT_TOKEN not found in environment variables")
                raise ValueError("TELEGRAM_BOT_TOKEN 환경변수를 설정해주세요.")
        
        log_debug(f"DEBUG: TELEGRAM_BOT_TOKEN found: {TELEGRAM_BOT_TOKEN[:10]}...")

        # 허용된 채팅방 ID 가져오기
        ALLOWED_CHAT_IDS_STR = os.getenv("ALLOWED_CHAT_IDS")
        if not ALLOWED_CHAT_IDS_STR:
            try:
                from config.telegram_config import ALLOWED_CHAT_IDS  # type: ignore
                ALLOWED_CHAT_IDS_STR = ALLOWED_CHAT_IDS
            except (ModuleNotFoundError, ImportError):
                ALLOWED_CHAT_IDS_STR = None
        
        allowed_chat_ids = []
        if ALLOWED_CHAT_IDS_STR:
            allowed_chat_ids = [int(chat_id.strip()) for chat_id in ALLOWED_CHAT_IDS_STR.split(",") if chat_id.strip()]
        
        log_debug(f"DEBUG: Application initialized - allowed_chat_ids: {allowed_chat_ids}")

        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        def get_chat_id(update):
            """업데이트에서 채팅방 ID 가져오기"""
            if update.message:
                return update.message.chat.id
            elif update.edited_message:
                return update.edited_message.chat.id
            elif update.channel_post:
                return update.channel_post.chat.id
            elif update.edited_channel_post:
                return update.edited_channel_post.chat.id
            return None

        def is_allowed_chat(chat_id):
            """채팅방이 허용된 목록에 있는지 확인"""
            if chat_id is None:
                return False
            if not allowed_chat_ids:
                return True
            return chat_id in allowed_chat_ids

        async def start_command(update, context):
            message = update.message or update.channel_post or update.edited_message or update.edited_channel_post
            if not message:
                return
            
            chat_id = get_chat_id(update)
            if not is_allowed_chat(chat_id):
                log_debug(f"DEBUG: Chat {chat_id} is not allowed")
                return
            
            welcome_message = (
                "🏠 담보대출 계산기 봇에 오신 것을 환영합니다!\n\n"
                "이 봇은 여러 금융사의 담보대출 한도와 금리를 계산해드립니다.\n\n"
                "📝 사용 방법:\n"
                "담보물건 정보를 메시지로 보내주시면 자동으로 계산해드립니다.\n\n"
                "💡 입력 예시:\n"
                "• 담보물건 주소: 서울특별시 강남구\n"
                "• KB시세: 5억원\n"
                "• 신용점수: 750점\n"
                "• 나이: 35세\n\n"
                "또는 실제 담보물건 정보를 그대로 복사해서 보내주셔도 됩니다.\n\n"
                "🔍 명령어:\n"
                "/start - 이 도움말 보기\n"
                "/help - 도움말 보기\n\n"
                "이제 담보물건 정보를 보내주시면 계산해드리겠습니다! 🚀"
            )
            try:
                await message.reply_text(welcome_message)
            except Exception as e:
                log_debug(f"DEBUG: Error sending welcome message: {str(e)}")

        async def handle_message(update, context=None):
            message = update.message or update.channel_post or update.edited_message or update.edited_channel_post
            
            if not message:
                return
            
            chat_id = get_chat_id(update)
            if not is_allowed_chat(chat_id):
                log_debug(f"DEBUG: Chat {chat_id} is not allowed")
                return
            
            message_text = message.text
            if not message_text:
                await message.reply_text(
                    "텍스트 메시지를 보내주세요.\n\n"
                    "담보물건 정보를 텍스트로 입력해주시면 계산해드립니다.\n\n"
                    "/start 명령어로 사용 방법을 확인하실 수 있습니다."
                )
                return
            
            try:
                parser = MessageParser()
                property_data = parser.parse(message_text)
                results = BaseCalculator.calculate_all_banks(property_data)
                formatted_result = format_all_results(results)
                await message.reply_text(formatted_result)
                log_debug(f"DEBUG: Message sent successfully to chat {chat_id}")
            except Exception as e:
                log_debug(f"DEBUG: Error in handle_message: {str(e)}")
                import traceback
                traceback.print_exc(file=sys.stderr)
                try:
                    await message.reply_text(
                        f"계산 중 오류가 발생했습니다.\n\n"
                        f"오류 내용: {str(e)}"
                    )
                except Exception:
                    pass

        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", start_command))
        application.add_handler(MessageHandler(~filters.COMMAND, handle_message))
        application._handle_message = handle_message
        
        log_debug("DEBUG: Telegram application handlers registered")

    return application


# handler 클래스 정의 전 로그
print("DEBUG: About to define handler function", file=sys.stderr, flush=True)
print("DEBUG: About to define handler function", flush=True)

def handler(request):
    """
    Vercel Python 서버리스 함수 핸들러
    Vercel Python은 Request 객체를 받아 Response를 반환합니다.
    """
    log_debug(f"DEBUG: ===== Request received =====")
    log_debug(f"DEBUG: Method: {request.method}")
    log_debug(f"DEBUG: Path: {request.path}")
    
    try:
        # GET 요청 처리 (헬스체크)
        if request.method == 'GET':
            log_debug("DEBUG: GET request received")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({"ok": True, "message": "Webhook endpoint is active"})
            }
        
        # POST 요청 처리 (텔레그램 웹훅)
        if request.method == 'POST':
            log_debug("DEBUG: ===== POST request received =====")
            
            # 요청 body 읽기
            body_str = request.body
            if not body_str:
                log_debug("DEBUG: Empty body, skipping")
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({"ok": True, "skipped": "empty body"})
                }
            
            # JSON 파싱
            try:
                body = json.loads(body_str) if isinstance(body_str, str) else body_str
            except (json.JSONDecodeError, TypeError):
                log_debug("DEBUG: Invalid JSON format")
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({"ok": True, "skipped": "invalid JSON"})
                }
            
            # 텔레그램 update 형식 검증
            if not isinstance(body, dict) or "update_id" not in body:
                log_debug("DEBUG: Not a telegram update, skipping")
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({"ok": True, "skipped": "not telegram update"})
                }
            
            log_debug(f"DEBUG: Telegram update received - update_id: {body.get('update_id')}")
            
            # 텔레그램 업데이트 처리
            from telegram import Update
            app = get_application()
            update = Update.de_json(body, app.bot)
            
            # 채팅방 ID 확인
            def get_chat_id_from_update(update):
                if update.message:
                    return update.message.chat.id
                elif update.edited_message:
                    return update.edited_message.chat.id
                elif update.channel_post:
                    return update.channel_post.chat.id
                elif update.edited_channel_post:
                    return update.edited_channel_post.chat.id
                return None
            
            chat_id = get_chat_id_from_update(update)
            log_debug(f"DEBUG: chat_id: {chat_id}")
            
            # 허용된 채팅방 ID 확인
            ALLOWED_CHAT_IDS_STR = os.getenv("ALLOWED_CHAT_IDS")
            if not ALLOWED_CHAT_IDS_STR:
                try:
                    from config.telegram_config import ALLOWED_CHAT_IDS  # type: ignore
                    ALLOWED_CHAT_IDS_STR = ALLOWED_CHAT_IDS
                except (ModuleNotFoundError, ImportError):
                    ALLOWED_CHAT_IDS_STR = None
            
            allowed_chat_ids = []
            if ALLOWED_CHAT_IDS_STR:
                allowed_chat_ids = [int(chat_id.strip()) for chat_id in ALLOWED_CHAT_IDS_STR.split(",") if chat_id.strip()]
            
            if allowed_chat_ids and chat_id not in allowed_chat_ids:
                log_debug(f"DEBUG: Chat {chat_id} is not in allowed list")
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({"ok": True, "skipped": "chat not allowed"})
                }
            
            # 비동기 처리
            async def process():
                try:
                    if not app._initialized:
                        await app.initialize()
                    
                    if update.channel_post or update.edited_message or update.edited_channel_post:
                        if hasattr(app, '_handle_message'):
                            await app._handle_message(update, None)
                        else:
                            await app.process_update(update)
                    else:
                        await app.process_update(update)
                    
                    log_debug("DEBUG: Message processing completed")
                except Exception as e:
                    log_debug(f"DEBUG: Error in process(): {str(e)}")
                    import traceback
                    traceback.print_exc(file=sys.stderr)
            
            # 이벤트 루프 실행
            global _global_loop
            
            try:
                loop = asyncio.get_running_loop()
                log_debug("DEBUG: Event loop already running, using thread")
                import threading
                import queue
                
                exception_queue = queue.Queue()
                
                def run_in_new_thread():
                    global _global_loop
                    try:
                        if _global_loop is None or _global_loop.is_closed():
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                        else:
                            new_loop = _global_loop
                            asyncio.set_event_loop(new_loop)
                        
                        new_loop.run_until_complete(process())
                        
                        if not new_loop.is_closed():
                            _global_loop = new_loop
                    except Exception as e:
                        exception_queue.put(e)
                
                thread = threading.Thread(target=run_in_new_thread, daemon=False)
                thread.start()
                thread.join(timeout=25)
                
                if not exception_queue.empty():
                    raise exception_queue.get()
                
                if thread.is_alive():
                    log_debug("DEBUG: Thread timeout")
                    raise TimeoutError("Process timeout")
                    
            except RuntimeError:
                log_debug("DEBUG: No running loop, creating new one")
                
                if _global_loop is None or _global_loop.is_closed():
                    _global_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(_global_loop)
                
                try:
                    _global_loop.run_until_complete(process())
                except Exception as e:
                    log_debug(f"DEBUG: Error in process: {str(e)}")
            
            except Exception as e:
                log_debug(f"DEBUG: Event loop error: {str(e)}")
                import traceback
                traceback.print_exc(file=sys.stderr)
            
            log_debug("DEBUG: ===== POST request completed =====")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({"ok": True})
            }
        
        # 다른 메서드는 405 반환
        return {
            'statusCode': 405,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({"error": "Method not allowed"})
        }
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        log_debug(f"ERROR: Error processing request: {error_msg}")
        log_debug(traceback_str)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({"error": error_msg})
        }

# 모듈 로드 완료 (즉시 실행)
print("DEBUG: api/webhook.py module initialization complete", file=sys.stderr, flush=True)
print(f"DEBUG: handler function ready: {handler}", file=sys.stderr, flush=True)
print("DEBUG: api/webhook.py module initialization complete", flush=True)
print(f"DEBUG: handler function ready: {handler}", flush=True)
log_debug("DEBUG: api/webhook.py module initialization complete")
log_debug(f"DEBUG: handler function ready: {handler}")
