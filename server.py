import socketio
from aiohttp import web
import asyncio
import random
import time
import os
import json
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# إنشاء سيرفر Socket.IO مع تكوين CORS المناسب
sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='aiohttp')
app = web.Application()
sio.attach(app)

# متغيرات عامة للعبة
connected_players = {}
ready_players = set()
frozen_players = set()
punishments_list = []
used_punishments = []
player_answers = {}
question_number = 0
final_punishment_data = {}
surprise_ready = {}
final_losers = []
game_in_progress = False
current_round_data = None

# قاعدة بيانات الأسئلة
questions_bank = [
    # الأسئلة الأصلية
    {"question": "ما هي عاصمة فرنسا؟", "options": ["باريس", "روما", "مدريد", "برلين"], "correct": "باريس"},
    {"question": "ما هو أكبر كوكب في المجموعة الشمسية؟", "options": ["المريخ", "زحل", "الأرض", "المشتري"], "correct": "المشتري"},
    {"question": "كم عدد أيام السنة الكبيسة؟", "options": ["365", "366", "364", "367"], "correct": "366"},
    {"question": "من اخترع المصباح الكهربائي؟", "options": ["أديسون", "نيوتن", "أينشتاين", "بيل"], "correct": "أديسون"},
    {"question": "ما البحر الذي يطل على السعودية؟", "options": ["الأحمر", "المتوسط", "العربي", "الكاريبي"], "correct": "الأحمر"},
    
    # أسئلة جغرافية مبسطة
    {"question": "ما هي عاصمة مصر؟", "options": ["القاهرة", "الرياض", "دبي", "بيروت"], "correct": "القاهرة"},
    {"question": "ما هي أكبر دولة عربية من حيث المساحة؟", "options": ["مصر", "السعودية", "الجزائر", "السودان"], "correct": "الجزائر"},
    {"question": "أي قارة توجد فيها أستراليا؟", "options": ["آسيا", "أمريكا", "أوروبا", "أوقيانوسيا"], "correct": "أوقيانوسيا"},
    {"question": "ما هي عاصمة السعودية؟", "options": ["جدة", "الرياض", "مكة", "المدينة"], "correct": "الرياض"},
    {"question": "ما هو أطول نهر في العالم؟", "options": ["النيل", "الأمازون", "المسيسيبي", "دجلة"], "correct": "النيل"},
    {"question": "في أي دولة توجد مدينة جدة؟", "options": ["مصر", "الإمارات", "السعودية", "الكويت"], "correct": "السعودية"},
    {"question": "أي مدينة هي عاصمة الإمارات العربية المتحدة؟", "options": ["دبي", "الشارقة", "أبوظبي", "عجمان"], "correct": "أبوظبي"},
    {"question": "ما هي أكبر دولة في العالم من حيث المساحة؟", "options": ["الصين", "كندا", "الولايات المتحدة", "روسيا"], "correct": "روسيا"},
    
    # أسئلة عامة بسيطة
    {"question": "ما هو لون السماء في النهار؟", "options": ["أزرق", "أحمر", "أخضر", "أصفر"], "correct": "أزرق"},
    {"question": "كم يوم في الأسبوع؟", "options": ["5", "6", "7", "8"], "correct": "7"},
    {"question": "ما هو الحيوان الذي له خرطوم طويل؟", "options": ["الزرافة", "الفيل", "الأسد", "النمر"], "correct": "الفيل"},
    {"question": "كم ساعة في اليوم؟", "options": ["12", "18", "24", "36"], "correct": "24"},
    {"question": "أي من هذه الفواكه حمراء عادةً؟", "options": ["التفاح", "الموز", "البرتقال", "الكيوي"], "correct": "التفاح"},
    {"question": "ما هو المعدن الذي يستخدم في صناعة العملات المعدنية غالباً؟", "options": ["الذهب", "الحديد", "النحاس", "الفضة"], "correct": "النحاس"},
    {"question": "ما هو عدد أرجل العنكبوت؟", "options": ["4", "6", "8", "10"], "correct": "8"},
    {"question": "ما عدد شهور السنة؟", "options": ["10", "11", "12", "13"], "correct": "12"},
    
    # باقي الأسئلة
    {"question": "كم عدد لاعبي فريق كرة القدم على أرض الملعب؟", "options": ["9", "10", "11", "12"], "correct": "11"},
    {"question": "ما هي الرياضة التي تلعب بالمضرب والريشة؟", "options": ["التنس", "كرة الطاولة", "الريشة الطائرة", "الاسكواش"], "correct": "الريشة الطائرة"},
    {"question": "أي دولة فازت بكأس العالم لكرة القدم 2022؟", "options": ["البرازيل", "فرنسا", "الأرجنتين", "إنجلترا"], "correct": "الأرجنتين"},
    {"question": "ما هي الرياضة التي يسجل فيها هدف في مرمى؟", "options": ["كرة القدم", "كرة السلة", "التنس", "الجولف"], "correct": "كرة القدم"},
    {"question": "كم نقطة يحصل عليها الفريق عند تسجيل هدف في كرة القدم؟", "options": ["1", "2", "3", "5"], "correct": "1"},
    {"question": "من هو اللاعب المشهور بلقب (الأسطورة) في كرة القدم؟", "options": ["ميسي", "رونالدو", "بيليه", "مارادونا"], "correct": "بيليه"},
    {"question": "ما هي الرياضة التي تلعب في الماء؟", "options": ["كرة اليد", "كرة السلة", "كرة الماء", "كرة الطائرة"], "correct": "كرة الماء"},
    {"question": "أي من هذه الرياضات لا تستخدم الكرة؟", "options": ["كرة القدم", "كرة السلة", "السباحة", "كرة اليد"], "correct": "السباحة"},
    {"question": "ما هو طعام يابان الشهير المصنوع من الأرز والسمك؟", "options": ["البيتزا", "البرغر", "السوشي", "الكبسة"], "correct": "السوشي"},
    {"question": "ما هي الفاكهة المعروفة بـ 'ملك الفواكه'؟", "options": ["التفاح", "الموز", "المانجو", "الدوريان"], "correct": "الدوريان"},
    {"question": "أي من هذه المشروبات يحتوي على الكافيين؟", "options": ["عصير البرتقال", "الحليب", "القهوة", "الليمون"], "correct": "القهوة"},
    {"question": "ما هو الطبق السعودي الشهير المصنوع من الأرز واللحم؟", "options": ["المندي", "الكبسة", "المقلوبة", "البرياني"], "correct": "الكبسة"},
    {"question": "ما هي الخضار الحمراء التي تستخدم في صلصة المعكرونة؟", "options": ["الخيار", "الطماطم", "الباذنجان", "الجزر"], "correct": "الطماطم"},
    {"question": "ما هو نوع الطعام الذي تشتهر به إيطاليا؟", "options": ["السوشي", "الباستا", "الكبسة", "الكاري"], "correct": "الباستا"},
    {"question": "أي من هذه المأكولات يصنع أساسًا من الحليب؟", "options": ["الخبز", "الجبن", "البطاطس", "الأرز"], "correct": "الجبن"},
    {"question": "ما هي المادة التي تجعل الخبز ينتفخ؟", "options": ["السكر", "الملح", "الخميرة", "الماء"], "correct": "الخميرة"},
    {"question": "ما هو الحيوان الذي له أذنان طويلتان ويأكل الجزر؟", "options": ["القط", "الكلب", "الأرنب", "الفأر"], "correct": "الأرنب"},
    {"question": "ما هو أسرع حيوان في العالم؟", "options": ["النمر", "الفهد", "الأسد", "الغزال"], "correct": "الفهد"},
    {"question": "أي من هذه الحيوانات يعيش في الماء؟", "options": ["الأسد", "الفيل", "الجمل", "الحوت"], "correct": "الحوت"},
    {"question": "ما هو الطائر الذي لا يطير؟", "options": ["النسر", "البطريق", "الحمام", "البط"], "correct": "البطريق"},
    {"question": "ما هو الحيوان الذي له قرون ويعطي الحليب؟", "options": ["الأسد", "البقرة", "الكلب", "الفأر"], "correct": "البقرة"},
    {"question": "ما هو صوت القط؟", "options": ["نباح", "مواء", "خوار", "نهيق"], "correct": "مواء"},
    {"question": "ما هو الحيوان الأكبر في العالم؟", "options": ["الفيل", "الزرافة", "الحوت الأزرق", "وحيد القرن"], "correct": "الحوت الأزرق"},
    {"question": "أي من هذه الحيوانات يمكنه الطيران؟", "options": ["البطريق", "النعامة", "الدجاجة", "الخفاش"], "correct": "الخفاش"},
    {"question": "ما هي وسيلة النقل التي تسير على السكك الحديدية؟", "options": ["السيارة", "الطائرة", "القطار", "الدراجة"], "correct": "القطار"},
    {"question": "ما هي وسيلة النقل التي تطير في السماء؟", "options": ["السيارة", "الطائرة", "القارب", "الدراجة"], "correct": "الطائرة"},
    {"question": "ما هي وسيلة النقل التي لها عجلتان؟", "options": ["السيارة", "الشاحنة", "الحافلة", "الدراجة"], "correct": "الدراجة"},
    {"question": "ما هي وسيلة النقل التي تستخدم في البحر؟", "options": ["السيارة", "الطائرة", "القارب", "الدراجة"], "correct": "القارب"},
    {"question": "أي من وسائل النقل التالية هي الأسرع؟", "options": ["السيارة", "الطائرة", "القطار", "الحافلة"], "correct": "الطائرة"},
    {"question": "ما هي وسيلة النقل التي تعمل بالكهرباء غالباً؟", "options": ["الترام", "الطائرة", "السفينة", "الدراجة"], "correct": "الترام"},
    {"question": "ما هو المكان المخصص لهبوط وإقلاع الطائرات؟", "options": ["الميناء", "المطار", "محطة القطار", "موقف الباصات"], "correct": "المطار"},
    {"question": "ما هي وسيلة النقل التي تحمل الكثير من الركاب في المدينة؟", "options": ["الدراجة", "السيارة", "الحافلة", "الشاحنة"], "correct": "الحافلة"},
    {"question": "ما هو اللون الناتج عن خلط الأزرق والأصفر؟", "options": ["أحمر", "أخضر", "برتقالي", "بنفسجي"], "correct": "أخضر"},
    {"question": "ما هو لون علم المملكة العربية السعودية؟", "options": ["أخضر", "أحمر", "أزرق", "أصفر"], "correct": "أخضر"},
    {"question": "ما هو لون الطماطم الناضجة؟", "options": ["أخضر", "أحمر", "أصفر", "برتقالي"], "correct": "أحمر"},
    {"question": "ما هو اللون الناتج عن خلط الأحمر والأصفر؟", "options": ["أرجواني", "أزرق", "برتقالي", "أخضر"], "correct": "برتقالي"},
    {"question": "ما هو لون الموز الناضج؟", "options": ["أخضر", "أحمر", "أصفر", "برتقالي"], "correct": "أصفر"},
    {"question": "ما هو لون السماء صافية في النهار؟", "options": ["رمادي", "أزرق", "أبيض", "أسود"], "correct": "أزرق"},
    {"question": "ما هو لون الثلج؟", "options": ["أبيض", "أزرق", "شفاف", "رمادي"], "correct": "أبيض"},
    {"question": "ما هو لون العشب؟", "options": ["أصفر", "أحمر", "أزرق", "أخضر"], "correct": "أخضر"}
]

# --- معالجين الصفحات الثابتة ---
async def index(request): 
    return web.FileResponse('./frontend/index.html')

async def player_page(request): 
    return web.FileResponse('./frontend/players.html')

async def manager_page(request): 
    return web.FileResponse('./frontend/manager.html')

async def static_file(request):
    filename = request.match_info.get('filename')
    filepath = os.path.join('./frontend/static', filename)
    if os.path.exists(filepath):
        return web.FileResponse(filepath)
    else:
        return web.Response(text="File not found", status=404)

# --- إعداد المسارات ---
app.router.add_get('/', index)
app.router.add_get('/player', player_page)
app.router.add_get('/manager', manager_page)
app.router.add_get('/static/{filename}', static_file)

# --- وظائف المساعدة ---
async def update_leaderboard():
    """تحديث لوحة المتصدرين وإرسالها لجميع اللاعبين"""
    leaderboard = sorted([
        {"name": info['name'], "score": info['score']} 
        for sid, info in connected_players.items()
    ], key=lambda x: -x['score'])
    
    await sio.emit("leaderboard_update", leaderboard)
    await sio.emit("leaderboard_chart", leaderboard)
    logger.info(f"تم تحديث لوحة المتصدرين: {leaderboard}")

async def save_game_state():
    """حفظ حالة اللعبة في ملف للاستعادة في حالة إعادة تشغيل السيرفر"""
    global connected_players, ready_players, frozen_players, punishments_list, question_number
    
    state = {
        "connected_players": {k: v for k, v in connected_players.items() if isinstance(k, str)},
        "ready_players": list(ready_players),
        "frozen_players": list(frozen_players),
        "punishments_list": punishments_list,
        "question_number": question_number,
        "game_in_progress": game_in_progress
    }
    
    try:
        with open("game_state.json", "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        logger.info("تم حفظ حالة اللعبة بنجاح")
    except Exception as e:
        logger.error(f"خطأ في حفظ حالة اللعبة: {e}")

async def load_game_state():
    """تحميل حالة اللعبة من ملف في حالة إعادة تشغيل السيرفر"""
    global connected_players, ready_players, frozen_players, punishments_list, question_number, game_in_progress
    
    try:
        if os.path.exists("game_state.json"):
            with open("game_state.json", "r", encoding="utf-8") as f:
                state = json.load(f)
                
            connected_players = state.get("connected_players", {})
            ready_players = set(state.get("ready_players", []))
            frozen_players = set(state.get("frozen_players", []))
            punishments_list = state.get("punishments_list", [])
            question_number = state.get("question_number", 0)
            game_in_progress = state.get("game_in_progress", False)
            
            logger.info("تم تحميل حالة اللعبة بنجاح")
            return True
        return False
    except Exception as e:
        logger.error(f"خطأ في تحميل حالة اللعبة: {e}")
        return False

async def reset_game():
    """إعادة تعيين حالة اللعبة"""
    global question_number, frozen_players, player_answers, final_punishment_data
    global final_losers, game_in_progress, surprise_ready, used_punishments, current_round_data
    
    question_number = 0
    frozen_players.clear()
    player_answers.clear()
    final_punishment_data.clear()
    final_losers.clear()
    game_in_progress = False
    surprise_ready.clear()
    used_punishments.clear()
    current_round_data = None
    
    # إعادة تعيين النقاط لجميع اللاعبين
    for sid in connected_players:
        connected_players[sid]['score'] = 0
    
    await update_leaderboard()
    await sio.emit("game_reset")
    logger.info("تم إعادة تعيين اللعبة")

# --- أحداث Socket.IO ---
@sio.event
async def connect(sid, environ):
    """التعامل مع اتصال لاعب جديد"""
    logger.info(f"✅ اتصال جديد: {sid}")
    await sio.emit("connection_success", room=sid)
    
    # إرسال حالة اللعبة الحالية إذا كانت اللعبة جارية
    if game_in_progress:
        await sio.emit("game_in_progress", room=sid)

@sio.event
async def disconnect(sid):
    """التعامل مع انقطاع اتصال لاعب"""
    if sid in connected_players:
        player_name = connected_players[sid]['name']
        logger.info(f"❌ انقطع اتصال اللاعب: {player_name} ({sid})")
        
        # إزالة اللاعب من القوائم
        if sid in ready_players:
            ready_players.remove(sid)
        if sid in frozen_players:
            frozen_players.remove(sid)
        if sid in player_answers:
            del player_answers[sid]
        
        # إبلاغ جميع اللاعبين بانقطاع اللاعب
        await sio.emit("player_disconnected", {"name": player_name})
        
        # حذف اللاعب من المتصلين
        del connected_players[sid]
        await update_leaderboard()

@sio.event
async def register_name(sid, name):
    """تسجيل اسم لاعب جديد"""
    try:
        # التحقق من صحة الاسم
        if not name or not isinstance(name, str) or len(name.strip()) == 0:
            await sio.emit("registration_error", {"message": "الرجاء إدخال اسم صحيح"}, room=sid)
            return
            
        # التحقق من عدم تكرار الاسم
        for existing_sid, info in connected_players.items():
            if info['name'].lower() == name.lower() and existing_sid != sid:
                await sio.emit("registration_error", {"message": "هذا الاسم مستخدم بالفعل، الرجاء اختيار اسم آخر"}, room=sid)
                return

        connected_players[sid] = {"name": name, "score": 0}
        logger.info(f"✅ تم تسجيل لاعب جديد: {name} ({sid})")
        
        # إبلاغ جميع اللاعبين بانضمام لاعب جديد
        await sio.emit("new_player", {"name": name, "sid": sid})
        
        # إرسال قائمة اللاعبين الحاليين للاعب الجديد
        player_list = [{"name": info['name'], "score": info['score']} for s, info in connected_players.items()]
        await sio.emit("current_players", player_list, room=sid)
        
        await update_leaderboard()
    except Exception as e:
        logger.error(f"خطأ في تسجيل اللاعب: {e}")
        await sio.emit("registration_error", {"message": "حدث خطأ أثناء التسجيل، الرجاء المحاولة مرة أخرى"}, room=sid)

@sio.event
async def confirm_ready(sid):
    """تأكيد استعداد اللاعب للعب"""
    if sid not in connected_players:
        return
        
    ready_players.add(sid)
    player_name = connected_players[sid]['name']
    logger.info(f"👍 اللاعب جاهز: {player_name} ({sid})")
    
    # إبلاغ جميع اللاعبين باستعداد لاعب
    await sio.emit("player_ready", {"name": player_name})
    
    # التحقق من استعداد جميع اللاعبين
    if ready_players and len(ready_players) == len(connected_players):
        await sio.emit("registration_completed")
        await sio.emit("play_start_sound")
        logger.info("🎮 جميع اللاعبين جاهزون للعب!")

@sio.event
async def selected_punishments(sid, data):
    """تحديد قائمة العقوبات التي سيتم استخدامها في اللعبة"""
    global punishments_list, used_punishments
    
    try:
        if not isinstance(data, list):
            logger.error(f"خطأ في تنسيق العقوبات: {data}")
            return
            
        punishments_list = data
        used_punishments = []
        logger.info(f"✅ تم تحديد العقوبات: {len(punishments_list)} عقوبة")
        await sio.emit("punishments_confirmed", {"count": len(punishments_list)})
    except Exception as e:
        logger.error(f"خطأ في تحديد العقوبات: {e}")

@sio.event
async def answer(sid, data):
    """استقبال إجابة من لاعب"""
    # التحقق من صحة البيانات
    if sid in frozen_players or sid not in player_answers:
        return
        
    if not isinstance(data, dict):
        logger.error(f"خطأ في تنسيق الإجابة: {data}")
        return
        
    answer = data.get("answer")
    question_index = data.get("question_index")
    
    if answer is None or question_index is None:
        return
        
    try:
        question_index = int(question_index)
        answers = player_answers[sid]["answers"]
        
        # ضمان وجود مكان للإجابة في المصفوفة
        if len(answers) <= question_index:
            answers.extend([None] * (question_index - len(answers) + 1))
            
        answers[question_index] = (answer, time.time())
        
        # تسجيل الإجابة
        player_name = connected_players[sid]['name']
        logger.info(f"📝 إجابة من {player_name} للسؤال {question_index}: {answer}")
        
        # إشعار اللاعب بتلقي إجابته
        await sio.emit("answer_received", {"index": question_index}, room=sid)
    except Exception as e:
        logger.error(f"خطأ في معالجة الإجابة: {e}")

@sio.event
async def freeze_player(sid, target_name):
    """تجميد لاعب معين"""
    if sid not in connected_players:
        return
        
    freezer_name = connected_players[sid]['name']
    
    # البحث عن هدف التجميد
    for target_sid, info in connected_players.items():
        if info['name'] == target_name:
            frozen_players.add(target_sid)
            
            # إبلاغ اللاعب المجمد
            await sio.emit("player_frozen", {"by": freezer_name}, room=target_sid)
            
            # إبلاغ جميع اللاعبين
            await sio.emit("player_frozen_announcement", {
                "target": target_name,
                "by": freezer_name
            })
            
            logger.info(f"❄️ تم تجميد اللاعب {target_name} بواسطة {freezer_name}")
            break

@sio.event
async def start_game_signal(sid):
    """بدء اللعبة من قبل المدير"""
    global game_in_progress
    
    if game_in_progress:
        await sio.emit("game_already_in_progress", room=sid)
        return
        
    if len(ready_players) < 2:
        await sio.emit("not_enough_players", room=sid)
        return
        
    game_in_progress = True
    logger.info("🎮 بدء اللعبة!")
    await sio.emit("game_started")
    
    # بدء العد التنازلي قبل الجولة الأولى
    await sio.emit("pregame_countdown", {"duration": 10})
    await sio.emit("play_start_sound")
    
    # بدء اللعبة بعد العد التنازلي
    asyncio.create_task(start_elimination_game())

@sio.event
async def surprise_choice(sid, data):
    """اختيار نوع المفاجأة من قبل اللاعب الفائز"""
    if sid not in surprise_ready:
        logger.error(f"محاولة اختيار مفاجأة من لاعب غير مؤهل: {sid}")
        return
        
    if not isinstance(data, dict) or 'type' not in data:
        logger.error(f"تنسيق بيانات مفاجأة غير صحيح: {data}")
        return
        
    surprise_type = data['type']
    if surprise_type not in ['freeze', 'steal', 'swap']:
        logger.error(f"نوع مفاجأة غير صالح: {surprise_type}")
        return
        
    surprise_ready[sid] = surprise_type
    player_name = connected_players[sid]['name']
    logger.info(f"🎁 اللاعب {player_name} اختار مفاجأة: {surprise_type}")
    
    # الحصول على قائمة اللاعبين النشطين لاختيار الهدف
    active_names = [
        info['name'] 
        for s, info in connected_players.items() 
        if s != sid and s not in frozen_players and s in player_answers
    ]
    
    # إرسال قائمة اللاعبين المتاحين للاختيار
    await sio.emit("choose_target_player", {
        "surprise_type": surprise_type, 
        "players": active_names
    }, room=sid)

@sio.event
async def surprise_target_selected(sid, data):
    """معالجة اختيار هدف المفاجأة"""
    surprise_type = surprise_ready.get(sid)
    if not surprise_type:
        logger.error(f"محاولة تحديد هدف بدون اختيار مفاجأة مسبقاً: {sid}")
        return
        
    if not isinstance(data, dict) or 'target' not in data:
        logger.error(f"تنسيق بيانات الهدف غير صحيح: {data}")
        return
        
    target_name = data['target']
    player_name = connected_players[sid]['name']
    
    # البحث عن هدف المفاجأة
    target_sid = None
    for s, info in connected_players.items():
        if info['name'] == target_name:
            target_sid = s
            break
            
    if not target_sid:
        logger.error(f"لم يتم العثور على اللاعب الهدف: {target_name}")
        return
        
    # حذف حالة المفاجأة بعد الاستخدام
    del surprise_ready[sid]
    
    # تنفيذ المفاجأة حسب النوع
    if surprise_type == "freeze":
        # تجميد اللاعب الهدف
        frozen_players.add(target_sid)
        await sio.emit("player_frozen", {"by": player_name}, room=target_sid)
        await sio.emit("player_frozen_announcement", {
            "target": target_name,
            "by": player_name,
            "by_surprise": True
        })
        logger.info(f"❄️ تم تجميد اللاعب {target_name} بواسطة مفاجأة من {player_name}")
        
    elif surprise_type == "steal":
        # سرقة نقاط من اللاعب الهدف
        stolen = min(4, connected_players[target_sid]['score'])
        if stolen > 0:
            connected_players[sid]['score'] += stolen
            connected_players[target_sid]['score'] -= stolen
            
            # إبلاغ اللاعبين
            await sio.emit("points_stolen", {
                "from": target_name,
                "to": player_name,
                "amount": stolen
            })
            
            logger.info(f"💰 تم سرقة {stolen} نقاط من {target_name} إلى {player_name}")
        else:
            await sio.emit("steal_failed", {"target": target_name}, room=sid)
        
    elif surprise_type == "swap":
        # تبديل النقاط مع اللاعب الهدف
        connected_players[sid]['score'], connected_players[target_sid]['score'] = connected_players[target_sid]['score'], connected_players[sid]['score']
        
        # إبلاغ اللاعبين
        await sio.emit("points_swapped", {"with": target_name}, room=sid)
        await sio.emit("points_swapped", {"with": player_name}, room=target_sid)
        await sio.emit("points_swap_announcement", {
            "player1": player_name,
            "player2": target_name,
            "score1": connected_players[sid]['score'],
            "score2": connected_players[target_sid]['score']
        })
        
        logger.info(f"🔄 تم تبديل النقاط بين {player_name} و {target_name}")
    
    # تحديث لوحة المتصدرين
    await update_leaderboard()

@sio.event
async def replay_crown(sid):
    """إعادة تشغيل تأثير التاج للفائز"""
    if sid in connected_players:
        winner_name = connected_players[sid]['name']
        await sio.emit("crown_winner", {"name": winner_name})
        logger.info(f"👑 إعادة عرض تاج الفائز: {winner_name}")

@sio.event
async def i_am_final_winner(sid):
    """إعلان الفائز النهائي وبدء مرحلة العقوبات"""
    if sid not in connected_players:
        return
        
    winner_name = connected_players[sid]['name']
    logger.info(f"🏆 الفائز النهائي: {winner_name}")
    
    # إعداد قائمة الخاسرين النهائيين
    all_losers = [
        info['name'] 
        for s, info in connected_players.items() 
        if s != sid and s in ready_players
    ]
    
    global final_losers
    final_losers = all_losers
    
    # إرسال بيانات المرحلة النهائية للفائز
    await sio.emit("final_stage_start", {
        "players": all_losers,
        "punishments": punishments_list
    }, room=sid)
    
    # إبلاغ جميع اللاعبين ببدء المرحلة النهائية
    await sio.emit("final_stage_announcement", {
        "winner": winner_name,
        "losers": all_losers
    })

@sio.event
async def set_final_loser(sid, data):
    """تحديد الخاسر النهائي لتطبيق العقوبة عليه"""
    global final_losers
    
    if not isinstance(data, dict) or 'loser' not in data:
        logger.error(f"تنسيق بيانات الخاسر النهائي غير صحيح: {data}")
        return
        
    loser = data.get("loser")
    
    # إضافة الخاسر للقائمة إذا لم يكن موجوداً بالفعل
    if loser and loser not in final_losers:
        final_losers.append(loser)
    
    # إبلاغ جميع اللاعبين بتحديد الخاسر
    await sio.emit("final_loser_selected", {"loser": loser})
    logger.info(f"😢 تم تحديد الخاسر النهائي: {loser}")

@sio.event
async def final_apply_punishment(sid, data):
    """تطبيق عقوبة على خاسر محدد"""
    if not isinstance(data, dict) or 'loser' not in data or 'punishment' not in data:
        logger.error(f"تنسيق بيانات العقوبة النهائية غير صحيح: {data}")
        return
        
    loser = data.get("loser")
    punishment = data.get("punishment")
    
    if not loser or not punishment:
        return
    
    # تخزين العقوبة النهائية في القاموس
    final_punishment_data[loser] = punishment
    
    # إضافة العقوبة إلى المستخدمة
    if punishment in punishments_list and punishment not in used_punishments:
        used_punishments.append(punishment)
    
    # إرسال التحديث إلى جميع اللاعبين
    await sio.emit("final_punishment", {
        "loser": loser,
        "punishment": punishment
    })
    
    logger.info(f"⚠️ تم تطبيق العقوبة على {loser}: {punishment}")

@sio.event
async def apply_all_punishments(sid, data):
    """تطبيق جميع العقوبات على الخاسرين دفعة واحدة"""
    if not isinstance(data, dict) or 'punishments' not in data:
        logger.error(f"تنسيق بيانات العقوبات متعددة غير صحيح: {data}")
        return
        
    punishments = data.get("punishments", [])
    
    for item in punishments:
        if isinstance(item, dict):
            loser = item.get("loser")
            punishment = item.get("punishment")
            
            if loser and punishment:
                final_punishment_data[loser] = punishment
                
                # إضافة العقوبة إلى المستخدمة
                if punishment in punishments_list and punishment not in used_punishments:
                    used_punishments.append(punishment)
                
                await sio.emit("final_punishment", {
                    "loser": loser,
                    "punishment": punishment
                })
                
                logger.info(f"⚠️ تم تطبيق العقوبة على {loser}: {punishment}")
    
    # إرسال تأكيد تطبيق جميع العقوبات
    await sio.emit("all_punishments_applied")
    logger.info("✅ تم تطبيق جميع العقوبات")

@sio.event
async def spin_flash_punishments(sid):
    """عرض العقوبات بشكل عشوائي كمؤثر بصري"""
    # البحث عن العقوبات المتبقية التي لم تستخدم
    remaining = [p for p in punishments_list if p not in used_punishments]
    
    if not remaining:
        await sio.emit("no_punishments_remaining", room=sid)
        return
    
    # اختيار عقوبات عشوائية للعرض
    sample_size = min(len(remaining), 5)
    random_punishments = random.sample(remaining, sample_size)
    
    await sio.emit("flash_punishments", {
        "punishments": random_punishments
    }, room=sid)
    
    logger.info(f"🎲 تم عرض {sample_size} عقوبات عشوائية")

@sio.event
async def reset_game_request(sid):
    """طلب إعادة تعيين اللعبة"""
    await reset_game()
    await save_game_state()

@sio.event
async def game_status_request(sid):
    """طلب الحصول على حالة اللعبة الحالية"""
    status = {
        "players_count": len(connected_players),
        "ready_count": len(ready_players),
        "game_in_progress": game_in_progress,
        "question_number": question_number,
        "punishments_count": len(punishments_list),
        "used_punishments_count": len(used_punishments)
    }
    
    await sio.emit("game_status", status, room=sid)

async def start_elimination_game():
    """بدء اللعبة الرئيسية مع نظام الإقصاء"""
    global question_number, frozen_players, player_answers, final_punishment_data, final_losers, current_round_data, game_in_progress
    
    try:
        # تأخير قبل بدء اللعبة
        await asyncio.sleep(13)
        await sio.emit("registration_ended")
        await asyncio.sleep(4)

        active_players = list(ready_players)
        eliminated_players = []  # لتتبع اللاعبين الذين خرجوا من اللعبة
        
        # جولات اللعبة
        while len(active_players) > 1:
            question_number += 1
            logger.info(f"🔄 بدء الجولة {question_number} مع {len(active_players)} لاعب نشط")
            
            await sio.emit("question_number", question_number)
            await sio.emit("play_round_sound")
            
            # بدء العد التنازلي للجولة
            await sio.emit("start_countdown", {"duration": 15})

            # اختيار أسئلة عشوائية للجولة
            round_questions = random.sample(questions_bank, 4)
            player_answers = {sid: {"answers": []} for sid in active_players}
            
            # تخزين بيانات الجولة الحالية
            current_round_data = {
                "questions": round_questions,
                "start_time": time.time()
            }

            # إرسال الأسئلة للاعبين
            for sid in active_players:
                if sid in frozen_players:
                    continue
                await sio.emit("round_questions", round_questions, room=sid)

            # انتظار انتهاء وقت الجولة
            await asyncio.sleep(15.5)

            # تقييم إجابات اللاعبين
            correct_answers = [q['correct'] for q in round_questions]
            scored_players = []

            for sid in active_players:
                if sid in frozen_players:
                    # اللاعبين المجمدين يحصلون على 0 نقاط ولكن لا يتم إقصاؤهم تلقائياً
                    scored_players.append((sid, 0, float('inf')))
                    continue
                    
                answers = player_answers[sid]["answers"]
                correct_count = 0
                total_time = 0
                current_time = time.time()
                
                # حساب الإجابات الصحيحة والوقت الإجمالي
                for i in range(4):
                    if i < len(answers) and answers[i] and answers[i][0] == correct_answers[i]:
                        correct_count += 1
                        total_time += answers[i][1]
                    else:
                        # إذا لم يجب اللاعب، استخدم الوقت الحالي (أبطأ)
                        total_time += current_time
                
                # تحديث نقاط اللاعب
                connected_players[sid]['score'] += correct_count
                scored_players.append((sid, correct_count, total_time))

            # ترتيب اللاعبين حسب عدد الإجابات الصحيحة ثم حسب السرعة
            scored_players.sort(key=lambda x: (-x[1], x[2]))
            await update_leaderboard()
            
            # إرسال نتائج الجولة لجميع اللاعبين
            round_results = []
            for sid, correct_count, total_time in scored_players:
                player_info = connected_players[sid]
                round_results.append({
                    "name": player_info['name'],
                    "correct": correct_count,
                    "score": player_info['score'],
                    "is_frozen": sid in frozen_players
                })
                
            await sio.emit("round_results", {
                "results": round_results,
                "correct_answers": correct_answers,
                "questions": [q["question"] for q in round_questions]
            })
            
            # تحديد الخاسر
            loser_sid = scored_players[-1][0]
            loser_name = connected_players[loser_sid]['name']
            logger.info(f"❌ الخاسر في الجولة {question_number}: {loser_name}")
            
            # إبلاغ الخاسر
            await sio.emit("you_lost", {
                "round": question_number,
                "correct": scored_players[-1][1]
            }, room=loser_sid)
            
            # إبلاغ جميع اللاعبين
            await sio.emit("player_eliminated", {
                "name": loser_name,
                "round": question_number
            })
            
            # إزالة الخاسر من اللاعبين النشطين
            active_players.remove(loser_sid)
            eliminated_players.append(loser_sid)
            
            # إعطاء وقت للإعلان عن نتائج الجولة
            await asyncio.sleep(5)

            # تكريم الفائز بالجولة
            winner_sid, winner_correct, winner_time = scored_players[0]
            winner_name = connected_players[winner_sid]['name']
            perfect_score = winner_correct == 4
            
            logger.info(f"🏅 الفائز في الجولة {question_number}: {winner_name} (عدد الإجابات الصحيحة: {winner_correct})")
            
            # إبلاغ الفائز
            await sio.emit("you_won", {
                "name": winner_name,
                "score": connected_players[winner_sid]['score'],
                "perfect": perfect_score,
                "fastest": True
            }, room=winner_sid)
            
            # إبلاغ جميع اللاعبين
            await sio.emit("round_winner", {
                "name": winner_name,
                "perfect": perfect_score
            })
            
            # مفاجأة في حالة الإجابة المثالية
            if perfect_score and len(active_players) > 1:
                await sio.emit("show_surprise_box", room=winner_sid)
                await sio.emit("play_alarm_sound")
                surprise_ready[winner_sid] = True
                
                # وقت لاختيار المفاجأة
                await asyncio.sleep(6)

            # إمكانية تجميد لاعب آخر للفائز
            if len(active_players) > 1:
                await sio.emit("ask_to_freeze", {
                    "players": [connected_players[s]['name'] for s in active_players if s != winner_sid]
                }, room=winner_sid)
                
                # وقت لاختيار لاعب للتجميد
                await asyncio.sleep(6)
            
            # إلغاء تجميد جميع اللاعبين للجولة التالية
            frozen_players.clear()
            await sio.emit("unfreeze_all")
            
            # تأخير قبل الجولة التالية
            await asyncio.sleep(3)
            await save_game_state()
        
        # إعلان الفائز النهائي
        if active_players:
            final_sid = active_players[0]
            winner_name = connected_players[final_sid]['name']
            
            # إعداد قائمة الخاسرين النهائية
            final_losers = [connected_players[s]['name'] for s in eliminated_players]
            
            logger.info(f"🏆 الفائز النهائي: {winner_name}")
            
            # إبلاغ جميع اللاعبين
            await sio.emit("final_winner", winner_name)
            await sio.emit("crown_winner", {"name": winner_name})
            
            # إرسال بيانات المرحلة النهائية للفائز
            await sio.emit("final_stage_start", {
                "players": final_losers,
                "punishments": punishments_list
            }, room=final_sid)
            
        game_in_progress = False
        await save_game_state()
        
    except Exception as e:
        logger.error(f"خطأ أثناء تشغيل اللعبة: {e}")
        game_in_progress = False
        await sio.emit("game_error", {"message": "حدث خطأ أثناء تشغيل اللعبة"})

# --- تشغيل التطبيق ---
async def on_startup(app):
    """يتم تنفيذها عند بدء تشغيل التطبيق"""
    logger.info("🚀 بدء تشغيل السيرفر...")
    
    # محاولة استعادة حالة اللعبة
    restored = await load_game_state()
    if restored:
        logger.info("✅ تم استعادة حالة اللعبة السابقة")
    else:
        logger.info("🆕 بدء من حالة جديدة")

# إضافة دالة بدء التشغيل
app.on_startup.append(on_startup)

if __name__ == '__main__':
    # ضمان وجود المجلدات المطلوبة
    os.makedirs('./frontend/static', exist_ok=True)
    
    # تشغيل السيرفر
    web.run_app(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))